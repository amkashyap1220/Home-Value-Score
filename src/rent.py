"""Rent by zip for the renters' version of the value map (added 2026-10-21; see the
change log in docs/decisions.md).

- rent         median gross rent, dollars a month (ACS B25064; gross rent includes
               utilities the tenant pays)
- renter_units renter-occupied homes (ACS B25003_E003), used for the minimum
- zori         Zillow Observed Rent Index for the latest month, context only: it only
               covers about 60% of the zips, so it is not used in the score

Output: data/processed/rent.csv
"""
import pandas as pd

from acs import table
from fetch import ROOT, fetch

ZORI = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    acs = pd.concat([table("b25064", ["B25064_E001"]), table("b25003", ["B25003_E003"])], axis=1)
    acs = acs.apply(pd.to_numeric, errors="coerce")
    acs = acs.mask(acs < 0)   # negative values are Census "not available" codes
    out = pd.DataFrame({"rent": acs.B25064_E001, "renter_units": acs.B25003_E003})

    zori = pd.read_csv(fetch(ZORI), dtype={"RegionName": str})
    month = zori.columns[-1]
    out["zori"] = zori.set_index("RegionName")[month].reindex(out.index)

    out = zips[["zcta"]].merge(out.rename_axis("zcta").reset_index(), on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/rent.csv", index=False, float_format="%.6g")
    print(f"{out.rent.notna().sum()} of {len(out)} zips have a median rent; "
          f"{out.zori.notna().sum()} have ZORI ({month}); corr(rent, ZORI) = {out.rent.corr(out.zori):.2f}")


if __name__ == "__main__":
    main()
