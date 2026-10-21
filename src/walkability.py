"""EPA National Walkability Index (Smart Location Database v3) by ZCTA.

The index is published for 2010-vintage block groups. Each 2020 block is matched to
the 2010 block it overlaps most (Census 2010-2020 block relationship files), which
gives its 2010 block group. The ZCTA score is the 2020-population-weighted average.

Output: data/processed/walkability.csv
"""
import io
import zipfile

import duckdb
import pandas as pd

from fetch import ROOT, fetch

SLD = "https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv"
REL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/t10t20/TAB2010_TAB2020_ST{fips}.zip"


def block_2020_to_bg_2010(fips):
    with zipfile.ZipFile(fetch(REL.format(fips=fips))) as z:
        rel = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep="|", dtype=str, encoding="utf-8-sig")
    rel["block"] = rel.STATE_2020 + rel.COUNTY_2020 + rel.TRACT_2020 + rel.BLK_2020
    rel["bg2010"] = rel.STATE_2010 + rel.COUNTY_2010 + rel.TRACT_2010 + rel.BLK_2010.str[0]
    rel["overlap"] = rel.AREALAND_INT.astype(float) + rel.AREAWATER_INT.astype(float) / 1e6  # land first
    rel = rel.sort_values("overlap").groupby("block").tail(1)
    return rel[["block", "bg2010"]]


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    blocks = pd.read_parquet(ROOT / "data/processed/blocks.parquet", columns=["block", "zcta", "pop"])
    blocks = blocks[blocks.zcta.isin(zips.zcta) & (blocks["pop"] > 0)]
    xwalk = pd.concat([block_2020_to_bg_2010(f) for f in ["17", "18"]])
    blocks = blocks.merge(xwalk, on="block", how="left")

    # GEOID columns in the CSV are in scientific notation, so rebuild the id from its parts
    sld = duckdb.sql(f"""
        select lpad(STATEFP::varchar, 2, '0') || lpad(COUNTYFP::varchar, 3, '0')
               || lpad(TRACTCE::varchar, 6, '0') || BLKGRPCE::varchar as bg2010,
               NatWalkInd as walk_index
        from read_csv('{fetch(SLD)}', header=true)
        where STATEFP in (17, 18)
    """).df()
    blocks = blocks.merge(sld, on="bg2010", how="left")
    print(f"blocks without a walkability value: {blocks.walk_index.isna().sum()} "
          f"({blocks.loc[blocks.walk_index.isna(), 'pop'].sum():,} people)")

    b = blocks.dropna(subset=["walk_index"])
    out = (b.assign(w=b.walk_index * b["pop"]).groupby("zcta")[["w", "pop"]].sum()
           .pipe(lambda d: (d.w / d["pop"]).rename("walk_index")).reset_index())
    out = zips[["zcta"]].merge(out, on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/walkability.csv", index=False, float_format="%.4g")
    print(out.walk_index.describe().to_string(), "\nmissing:", out.walk_index.isna().sum())


if __name__ == "__main__":
    main()
