"""School score by ZCTA.

1. District proficiency = mean of % proficient in ELA and in math, for two bands:
   grades 3-8 (IL: IAR, IN: ILEARN) and high school (IL: ACT grade 11, IN: SAT grade 11).
2. Each band is turned into a percentile among the state's geographic districts
   (within Illinois or within Indiana only, since the tests differ).
3. Each 2020 census block gets its grades 3-8 percentile from its unified or elementary
   district and its high school percentile from its unified or secondary district
   (Census 2020 block assignment files). The block's school percentile is the mean of
   the two (or whichever one exists).
4. The ZCTA value is the land-area-weighted mean over its blocks.

Districts are linked to Census/NCES ids through the NCES Common Core of Data
directory (via the Urban Institute Education Data API), which carries each
district's state id (Illinois RCDTS, Indiana corporation number).

Output: data/processed/schools.csv, data/processed/school_districts.csv
"""
import pandas as pd
import requests

from fetch import ROOT, fetch

IL_RC = "https://www.isbe.net/Documents/2025-Report-Card-Public-Data-Set.xlsx"
IN_DOE = "https://www.in.gov/doe/it/data-center-and-reports/Data-Files"
IN_ILEARN = f"{IN_DOE}/ILEARN-2026-Grade3-8-Final-Corporation.xlsx"
IN_SAT = f"{IN_DOE}/SAT-2026-Grade11-Corporation.xlsx"
CCD = "https://educationdata.urban.org/api/v1/school-districts/ccd/directory/2024/?fips={fips}"


def ccd_directory():
    rows = []
    for fips in (17, 18):
        path = fetch(CCD.format(fips=fips), name=f"ccd_directory_2024_{fips}.json")
        rows += requests.models.complexjson.loads(path.read_text())["results"]
    d = pd.DataFrame(rows)[["leaid", "lea_name", "state_leaid"]]
    d["state_id"] = d.state_leaid.str[3:]  # drop "IL-" / "IN-"
    return d


def illinois():
    df = pd.read_excel(fetch(IL_RC), sheet_name="ELAMathScience", dtype={"RCDTS": str})
    df = df[df.Level == "District"]
    cols = [f"% {s} Proficiency {b}" for s in ("ELA", "Math") for b in ("Grade 3 to 8", "High School")]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")  # suppressed cells become missing
    out = pd.DataFrame({
        "state_id": df.RCDTS.str[:14],  # RR-CCC-DDDD-TT, matches the CCD state id
        "name": df.District,
        "prof_3_8": df[["% ELA Proficiency Grade 3 to 8", "% Math Proficiency Grade 3 to 8"]].mean(axis=1, skipna=False),
        "prof_hs": df[["% ELA Proficiency High School", "% Math Proficiency High School"]].mean(axis=1, skipna=False),
    })
    out["state"] = "IL"
    return out


def indiana_sheet(path, sheet, total_label, pct_word):
    """Corporation id and the corporation-total percent column of an IDOE results sheet."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
    band, head = raw.iloc[4].ffill(), raw.iloc[5].astype(str)
    col = [i for i in range(raw.shape[1]) if band[i] == total_label and pct_word in head[i] and "%" in head[i]][0]
    body = raw.iloc[6:]
    return pd.Series(pd.to_numeric(body[col], errors="coerce").values * 100, index=body[0].str.zfill(4).values)


def indiana():
    il, sat = fetch(IN_ILEARN), fetch(IN_SAT)
    ela = indiana_sheet(il, "ELA", "Corporation Total", "Proficient")
    math = indiana_sheet(il, "Math", "Corporation Total", "Proficient")
    ebrw = indiana_sheet(sat, "EBRW", "Corporation Total", "Benchmark")
    smath = indiana_sheet(sat, "Math", "Corporation Total", "Benchmark")
    out = pd.DataFrame({"prof_3_8": (ela + math) / 2, "prof_hs": (ebrw + smath) / 2})
    out = out[out.index.str.fullmatch(r"\d{4}")]
    out.index.name = "state_id"
    out = out.reset_index()
    out["state"] = "IN"
    return out


def main():
    ccd = ccd_directory()
    results = pd.concat([illinois(), indiana()]).merge(ccd, on="state_id", how="inner")
    results["lea"] = results.leaid.str[2:]  # 5-digit Census school district code

    blocks = pd.read_parquet(ROOT / "data/processed/blocks.parquet")
    blocks = blocks[blocks.state.isin(["17", "18"])]
    geo = set(zip(blocks.state, blocks.sduni)) | set(zip(blocks.state, blocks.sdelm)) | set(zip(blocks.state, blocks.sdsec))
    results = results[[(s, l) in geo for s, l in zip(results.leaid.str[:2], results.lea)]].copy()

    # Percentiles within each state, among geographic districts with results
    for band in ["prof_3_8", "prof_hs"]:
        results[f"pct_{band[5:]}"] = results.groupby("state")[band].rank(pct=True) * 100
    results.to_csv(ROOT / "data/processed/school_districts.csv", index=False, float_format="%.4g")

    key = results.set_index(results.leaid.str[:2] + results.lea)
    st = blocks.state
    k8_district = st + blocks.sduni.fillna(blocks.sdelm).astype(str)
    hs_district = st + blocks.sduni.fillna(blocks.sdsec).astype(str)
    blocks = blocks.assign(
        pct_3_8=k8_district.map(key.pct_3_8),
        pct_hs=hs_district.map(key.pct_hs),
    )
    blocks["school_pct"] = blocks[["pct_3_8", "pct_hs"]].mean(axis=1)

    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    b = blocks[blocks.zcta.isin(zips.zcta) & (blocks.aland > 0)]
    covered = b.dropna(subset=["school_pct"])
    z = (covered.assign(w=covered.school_pct * covered.aland).groupby("zcta")[["w", "aland"]].sum()
         .pipe(lambda d: (d.w / d.aland).rename("school_pct")))
    share = (covered.groupby("zcta").aland.sum() / b.groupby("zcta").aland.sum()).rename("school_land_covered")
    out = zips[["zcta"]].merge(pd.concat([z, share], axis=1).reset_index(names="zcta"), on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/schools.csv", index=False, float_format="%.4g")

    missing_k8 = b[b.pct_3_8.isna()].groupby(k8_district).aland.sum().sort_values(ascending=False)
    missing_hs = b[b.pct_hs.isna()].groupby(hs_district).aland.sum().sort_values(ascending=False)
    print(f"districts with results: {len(results)} ({results.state.value_counts().to_dict()})")
    print("land in scope without a 3-8 district result (km2):", (missing_k8 / 1e6).round(1).head(10).to_dict())
    print("land in scope without a HS district result (km2):", (missing_hs / 1e6).round(1).head(10).to_dict())
    print(out.describe().to_string(), "\nmissing:", out.school_pct.isna().sum())


if __name__ == "__main__":
    main()
