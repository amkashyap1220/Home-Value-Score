"""Build a block-level table for IL, IN and WI: 2020 population, land area, ZCTA,
place and school districts. Everything population- or area-weighted later in the
project is aggregated from this table.

Output: data/processed/blocks.parquet
"""
import io
import zipfile

import duckdb
import pandas as pd
import pyogrio

from fetch import ROOT, fetch

CENSUS = "https://www2.census.gov/geo"
STATES = {"17": "IL", "18": "IN", "55": "WI"}  # WI only to get full populations of border ZCTAs


def read_blocks(fips):
    path = fetch(f"{CENSUS}/tiger/TIGER2020/TABBLOCK20/tl_2020_{fips}_tabblock20.zip")
    df = pyogrio.read_dataframe(path, columns=["GEOID20", "ALAND20", "POP20"], read_geometry=False)
    return df.rename(columns={"GEOID20": "block", "ALAND20": "aland", "POP20": "pop"})


def read_baf(fips, abbr, layer):
    path = fetch(f"{CENSUS}/docs/maps-data/data/baf2020/BlockAssign_ST{fips}_{abbr}.zip")
    name = f"BlockAssign_ST{fips}_{abbr}_{layer}.txt"
    with zipfile.ZipFile(path) as z:
        if name not in z.namelist():  # Indiana has only unified districts
            return pd.Series(dtype=str, name=layer.lower())
        raw = z.read(name)
    df = pd.read_csv(io.BytesIO(raw), sep="|", dtype=str)
    return df.set_index("BLOCKID").iloc[:, 0].rename(layer.lower())


def block_to_zcta():
    """Each block's ZCTA. A few blocks are split; keep the ZCTA with the most of the block's land."""
    path = fetch(f"{CENSUS}/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tabblock20_natl.txt")
    prefixes = ", ".join(f"'{s}'" for s in STATES)
    return duckdb.sql(f"""
        select GEOID_TABBLOCK_20 as block, arg_max(GEOID_ZCTA5_20, AREALAND_PART) as zcta
        from read_csv('{path}', delim='|', header=true, all_varchar=true)
        where left(GEOID_TABBLOCK_20, 2) in ({prefixes}) and GEOID_ZCTA5_20 is not null
        group by 1
    """).df()


def main():
    parts = []
    for fips, abbr in STATES.items():
        b = read_blocks(fips)
        if fips != "55":
            for layer in ["INCPLACE_CDP", "SDUNI", "SDELM", "SDSEC"]:
                b = b.join(read_baf(fips, abbr, layer), on="block")
        parts.append(b)
    blocks = pd.concat(parts, ignore_index=True)
    blocks = blocks.merge(block_to_zcta(), on="block", how="left")
    blocks["state"] = blocks.block.str[:2]
    blocks["county"] = blocks.block.str[:5]
    blocks["blockgroup"] = blocks.block.str[:12]
    blocks = blocks.rename(columns={"incplace_cdp": "place"})
    out = ROOT / "data" / "processed" / "blocks.parquet"
    blocks.to_parquet(out, index=False)
    print(f"{len(blocks):,} blocks, {blocks.zcta.notna().mean():.1%} with a ZCTA -> {out}")


if __name__ == "__main__":
    main()
