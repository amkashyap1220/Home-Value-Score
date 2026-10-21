"""Safety indicator by ZCTA from the FBI Crime Data Explorer.

Each zip is assigned one police agency: the municipal police department of the
incorporated place holding the largest share of the zip's 2020 population, or the
county sheriff if the largest share is unincorporated land (pre-registered rule).
Rate = (violent + property offenses in the latest full year) / agency population * 1,000.
If an agency's latest year is incomplete or clearly under-reported, its previous year
is used instead when that year covers all 12 months (Alex's choice, 2026-10-21).

Outputs:
  data/processed/crime.csv           one row per zip, with the agency and rate
  data/processed/crime_agencies.csv  one row per agency used, with months reported
"""
import json
import re

import pandas as pd
import pyogrio

from fetch import ROOT, fetch

CDE = "https://cde.ucr.cjis.gov/LATEST"
YEAR = 2025  # latest full year in the CDE on the pull date (data through 10/2026)
STATES = {"17": "IL", "18": "IN"}
MIN_MONTHS = 12  # a year counts only if the agency reported all 12 months
# Data-quality rule (docs/decisions.md change log): a YEAR total under half of the
# previous-year total, with at least 50 offenses that year, counts as under-reported.
# Incomplete or under-reported agencies fall back to the previous year.
DROP_RATIO, DROP_MIN_PREV = 0.5, 50



def places(fips):
    path = fetch(f"https://www2.census.gov/geo/tiger/TIGER2020/PLACE/tl_2020_{fips}_place.zip")
    df = pyogrio.read_dataframe(path, columns=["PLACEFP", "NAME", "NAMELSAD", "FUNCSTAT"], read_geometry=False)
    df["state"] = fips
    return df.rename(columns={"PLACEFP": "place", "NAME": "place_name", "NAMELSAD": "place_lsad"})


def agencies(abbr):
    path = fetch(f"{CDE}/agency/byStateAbbr/{abbr}", name=f"cde_agencies_{abbr}.json")
    df = pd.DataFrame([a for v in json.loads(path.read_text()).values() for a in v])
    return df.drop_duplicates("ori")


def norm(s):
    s = s.lower().replace("saint ", "st ").replace("st. ", "st ").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def assign_agency(zips, blocks, place_attrs):
    """For each zip, the area holding most of its population: an incorporated place or a county's unincorporated land."""
    b = blocks[blocks.zcta.isin(zips.zcta) & (blocks["pop"] > 0)].merge(
        place_attrs[["state", "place", "FUNCSTAT"]], on=["state", "place"], how="left")
    incorporated = b.FUNCSTAT.eq("A")
    b["area"] = b.state + b.place.where(incorporated, "U" + b.county.str[2:])
    g = b.groupby(["zcta", "area"])["pop"].sum().reset_index()
    g["share"] = g["pop"] / g.groupby("zcta")["pop"].transform("sum")
    top = g.sort_values("pop").groupby("zcta").tail(1)
    top["kind"] = top.area.str[2].map(lambda c: "sheriff" if c == "U" else "municipal")
    return top[["zcta", "area", "share", "kind"]]


def match(top, place_attrs):
    counties = pyogrio.read_dataframe(
        fetch("https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"),
        columns=["GEOID", "NAME"], read_geometry=False).set_index("GEOID").NAME
    names = place_attrs.assign(area=place_attrs.state + place_attrs.place).set_index("area").place_name
    ag = pd.concat([agencies(a).assign(state=f) for f, a in STATES.items()])
    ag["key"] = ag.agency_name.map(norm)

    rows = []
    for t in top.itertuples():
        st = t.area[:2]
        cand = ag[ag.state == st]
        if t.kind == "sheriff":
            county = counties[st + t.area[3:]]
            name = f"{county} County Sheriff"
            hit = cand[(cand.agency_type_name == "County") & cand.key.str.startswith(norm(name))]
            # Cook County's patrol agency is the Sheriff's Police Department
            if len(hit) > 1:
                hit = hit[hit.key.str.contains("police")] if hit.key.str.contains("police").any() else hit.head(1)
        else:
            name = names[t.area]
            hit = cand[(cand.agency_type_name == "City") & cand.key.isin(
                [norm(f"{name} Police Department"), norm(f"{name} Police Dept"), norm(f"{name} Police")])]
        rows.append({"zcta": t.zcta, "area_name": name, "kind": t.kind, "pop_share": t.share,
                     "ori": hit.ori.iloc[0] if len(hit) == 1 else None,
                     "agency_name": hit.agency_name.iloc[0] if len(hit) == 1 else None})
    return pd.DataFrame(rows)


def offenses(ori, year=YEAR):
    """Monthly offense counts (violent + property) and agency population for one year."""
    out = {}
    for offense in ["violent-crime", "property-crime"]:
        path = fetch(f"{CDE}/summarized/agency/{ori}/{offense}?from=01-{year}&to=12-{year}",
                     name=f"cde/{ori}_{offense}_{year}.json")
        d = json.loads(path.read_text())
        actual = {k: v for k, v in d["offenses"]["actuals"].items() if k.endswith(" Offenses")}
        months = {k: v for k, v in next(iter(actual.values()), {}).items() if v is not None}  # None = not reported
        pops = [v for k, v in d["populations"]["population"].items() if k not in ("Illinois", "Indiana", "United States")]
        out[offense] = (sum(months.values()), len(months), max(pops[0].values()) if pops else None)
    (v, vm, pop), (p, pm, _) = out["violent-crime"], out["property-crime"]
    return {"violent": v, "property": p, "months": min(vm, pm), "agency_pop": pop}


def main():
    (ROOT / "data/raw/cde").mkdir(parents=True, exist_ok=True)
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    blocks = pd.read_parquet(ROOT / "data/processed/blocks.parquet", columns=["zcta", "state", "county", "place", "pop"])
    place_attrs = pd.concat([places(f) for f in STATES])

    m = match(assign_agency(zips, blocks, place_attrs), place_attrs)
    used = m.dropna(subset=["ori"]).drop_duplicates("ori")
    stats = pd.DataFrame([{"ori": o, **offenses(o)} for o in used.ori])
    prev = pd.DataFrame([{"ori": o, **offenses(o, YEAR - 1)} for o in used.ori])
    total, prev_total = stats.violent + stats.property, prev.violent + prev.property
    prev_ok = (prev.months == MIN_MONTHS) & (prev.agency_pop > 0)
    stats["offenses_prev_year"] = prev_total.where(prev_ok)
    stats["change_vs_prev_year"] = total / stats.offenses_prev_year - 1
    stats["incomplete"] = (stats.months < MIN_MONTHS) | stats.agency_pop.isna() | (stats.agency_pop == 0)
    stats["under_reported"] = ~stats.incomplete & (stats.offenses_prev_year >= DROP_MIN_PREV) & (stats.change_vs_prev_year < DROP_RATIO - 1)
    use_prev = (stats.incomplete | stats.under_reported) & prev_ok
    stats["crime_year"] = YEAR
    stats.loc[use_prev, "crime_year"] = YEAR - 1
    stats.loc[(stats.incomplete | stats.under_reported) & ~prev_ok, "crime_year"] = None
    stats["crimes_per_1000"] = (total / stats.agency_pop * 1000).where(stats.crime_year == YEAR)
    stats.loc[use_prev, "crimes_per_1000"] = (prev_total / prev.agency_pop * 1000)[use_prev]
    agencies_used = used[["ori", "agency_name", "kind"]].merge(stats, on="ori")
    agencies_used.to_csv(ROOT / "data/processed/crime_agencies.csv", index=False, float_format="%.4g")

    out = zips[["zcta"]].merge(m, on="zcta", how="left").merge(
        stats[["ori", "months", "incomplete", "under_reported", "crime_year", "crimes_per_1000"]], on="ori", how="left")
    out["note"] = None
    out.loc[out.ori.isna(), "note"] = "no matching agency in the FBI CDE"
    out.loc[out.incomplete.eq(True), "note"] = f"agency reported fewer than {MIN_MONTHS} months of {YEAR}"
    out.loc[out.under_reported.eq(True), "note"] = f"{YEAR} offenses under half of {YEAR - 1} (likely incomplete reporting)"
    out.loc[out.crime_year.eq(YEAR - 1), "note"] += f"; used {YEAR - 1}"
    out.loc[out.ori.notna() & out.crimes_per_1000.isna(), "note"] += f"; {YEAR - 1} also incomplete, missing"
    out.to_csv(ROOT / "data/processed/crime.csv", index=False, float_format="%.4g")

    print(out.kind.value_counts().to_string())
    print("zips with a crime rate:", out.crimes_per_1000.notna().sum(), "of", len(out))
    print(out.crime_year.value_counts(dropna=False).to_string())
    print(out[out.note.notna()][["zcta", "area_name", "agency_name", "months", "note"]].to_string(index=False))


if __name__ == "__main__":
    main()
