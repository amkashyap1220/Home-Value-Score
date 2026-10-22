"""Housing stock by zip, used as controls in the housing value model (src/value_gap.py),
added 2026-10-22.

Price per square foot depends on what kind of home is selling: a downtown condo and a
suburban house of the same quality sell at very different prices per sq ft. Redfin's
"All Residential" median mixes the two, so the value model controls for the mix of the
housing stock (the closest free, zip-level measure available):

- sf_detached_share  share of homes that are single-family detached (ACS B25024_E002 / E001)
- median_rooms       median rooms per home (ACS B25018), a rough size proxy

Both describe all homes in the zip (owned and rented), not only the ones that sold.

Output: data/processed/structure.csv
"""
import pandas as pd

from acs import table
from fetch import ROOT


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    df = pd.concat([
        table("b25024", ["B25024_E001", "B25024_E002"]),
        table("b25018", ["B25018_E001"]),
    ], axis=1).loc[lambda d: d.index.isin(zips.zcta)].apply(pd.to_numeric, errors="coerce")
    df = df.mask(df < 0)
    out = pd.DataFrame(index=df.index)
    out["housing_units"] = df.B25024_E001
    out["sf_detached_share"] = df.B25024_E002 / df.B25024_E001
    out["median_rooms"] = df.B25018_E001
    out = zips[["zcta"]].merge(out.reset_index(names="zcta"), on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/structure.csv", index=False, float_format="%.5g")
    print(out.describe().T.round(3).to_string())


if __name__ == "__main__":
    main()
