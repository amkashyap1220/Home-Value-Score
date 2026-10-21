"""Name each zip after the Census place (incorporated place or CDP) holding the largest
share of its 2020 population, for labels on the map and in the outputs.

Output: data/processed/places.csv (every in-scope zip, with its top place and that
place's share of the zip's population)
"""
import pandas as pd
import pyogrio

from fetch import ROOT, fetch


def place_names():
    rows = []
    for fips, abbr in [("17", "IL"), ("18", "IN")]:
        path = fetch(f"https://www2.census.gov/geo/tiger/TIGER2020/PLACE/tl_2020_{fips}_place.zip")
        df = pyogrio.read_dataframe(path, columns=["PLACEFP", "NAME"], read_geometry=False)
        rows.append(df.assign(state=fips, abbr=abbr))
    return pd.concat(rows).rename(columns={"PLACEFP": "place", "NAME": "place_name"})


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    blocks = pd.read_parquet(ROOT / "data/processed/blocks.parquet", columns=["zcta", "state", "place", "pop"])
    b = blocks[blocks.zcta.isin(zips.zcta) & blocks.place.notna() & (blocks["pop"] > 0)]
    total = blocks[blocks.zcta.isin(zips.zcta)].groupby("zcta")["pop"].sum()

    g = b.groupby(["zcta", "state", "place"], as_index=False)["pop"].sum()
    top = g.sort_values("pop").groupby("zcta").tail(1).merge(place_names(), on=["state", "place"])
    top["place_share"] = top["pop"] / top.zcta.map(total)

    out = zips[["zcta"]].merge(top[["zcta", "place_name", "place_share"]], on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/places.csv", index=False, float_format="%.3f")
    print(f"{out.place_name.notna().sum()} of {len(out)} zips named")


if __name__ == "__main__":
    main()
