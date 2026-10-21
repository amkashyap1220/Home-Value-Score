"""Map the pre-registered reputation list (Niche 2026 Best Places to Live) to zips.

- Suburbs: a zip is on the list if the Census place (incorporated place or CDP)
  holding the largest share of its 2020 population is on the list.
- Chicago: if that place is Chicago, the zip is on the list if the City of Chicago
  neighborhood covering the largest share of the zip's area inside Chicago is on the list.

Output: data/processed/reputation_zips.csv (every in-scope zip, with its top place,
neighborhood and whether it is on the list)
"""
import geopandas as gpd
import pandas as pd
import pyogrio

from fetch import ROOT, fetch

# docs/decisions.md, "Reputation list"
LIST = {
    "IL": ["Clarendon Hills", "Naperville", "Riverside", "Buffalo Grove", "Kildeer", "Lincolnshire",
           "Western Springs", "Long Grove", "La Grange", "Hinsdale", "Vernon Hills", "River Forest",
           "Evanston", "Northbrook", "Bannockburn", "Wilmette"],
    "IN": ["Munster", "Chesterton", "Dyer", "Valparaiso", "Lakes of the Four Seasons", "St. John", "Schererville"],
}
CHICAGO_NEIGHBORHOODS = ["Printers Row", "West Loop", "Loop", "River North"]
CHICAGO = ("17", "14000")
NEIGHBORHOODS = "https://data.cityofchicago.org/download/9wp7-iasj/application%2Fzip"
ZCTA = "https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/tl_2020_us_zcta520.zip"


def place_names():
    rows = []
    for fips, abbr in [("17", "IL"), ("18", "IN")]:
        path = fetch(f"https://www2.census.gov/geo/tiger/TIGER2020/PLACE/tl_2020_{fips}_place.zip")
        df = pyogrio.read_dataframe(path, columns=["PLACEFP", "NAME"], read_geometry=False)
        rows.append(df.assign(state=fips, abbr=abbr))
    return pd.concat(rows).rename(columns={"PLACEFP": "place", "NAME": "place_name"})


def chicago_neighborhood(zctas):
    """Neighborhood with the largest share of each zip's area inside Chicago."""
    nb = pyogrio.read_dataframe(fetch(NEIGHBORHOODS, name="chicago_neighborhoods_2012.zip"))[["PRI_NEIGH", "geometry"]]
    z = gpd.read_file(fetch(ZCTA), bbox=tuple(nb.to_crs(4269).total_bounds), columns=["ZCTA5CE20"])
    z = z[z.ZCTA5CE20.isin(zctas)].to_crs(nb.crs)
    parts = gpd.overlay(z, nb, how="intersection")
    parts["area"] = parts.area
    top = parts.sort_values("area").groupby("ZCTA5CE20").tail(1)
    return top.set_index("ZCTA5CE20").PRI_NEIGH


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    blocks = pd.read_parquet(ROOT / "data/processed/blocks.parquet", columns=["zcta", "state", "place", "pop"])
    b = blocks[blocks.zcta.isin(zips.zcta) & blocks.place.notna() & (blocks["pop"] > 0)]
    total = blocks[blocks.zcta.isin(zips.zcta)].groupby("zcta")["pop"].sum()

    g = b.groupby(["zcta", "state", "place"], as_index=False)["pop"].sum()
    top = g.sort_values("pop").groupby("zcta").tail(1).merge(place_names(), on=["state", "place"])
    top["place_share"] = top["pop"] / top.zcta.map(total)
    top["on_list"] = [n in LIST[a] for n, a in zip(top.place_name, top.abbr)]

    is_chicago = (top.state == CHICAGO[0]) & (top.place == CHICAGO[1])
    top["chicago_neighborhood"] = top.zcta.map(chicago_neighborhood(top.loc[is_chicago, "zcta"]))
    top.loc[~is_chicago, "chicago_neighborhood"] = None
    top.loc[is_chicago, "on_list"] = top.loc[is_chicago, "chicago_neighborhood"].isin(CHICAGO_NEIGHBORHOODS)
    top["list_entry"] = top.chicago_neighborhood.where(is_chicago, top.place_name).where(top.on_list)

    out = zips[["zcta"]].merge(
        top[["zcta", "place_name", "place_share", "chicago_neighborhood", "on_list", "list_entry"]], on="zcta", how="left")
    out["on_list"] = out.on_list.fillna(False).astype(bool)
    out.to_csv(ROOT / "data/processed/reputation_zips.csv", index=False, float_format="%.3f")

    on = out[out.on_list]
    print(f"{len(on)} zips on the reputation list:")
    print(on.to_string(index=False))
    all_entries = [*LIST["IL"], *LIST["IN"], *CHICAGO_NEIGHBORHOODS]
    print("list entries with no zip:", sorted(set(all_entries) - set(on.list_entry)))


if __name__ == "__main__":
    main()
