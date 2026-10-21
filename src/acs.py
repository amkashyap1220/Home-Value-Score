"""Commute time and effective property tax rate by ZCTA from the ACS 5-year
summary files (no API key needed).

- commute_min = aggregate travel time to work (B08013) / workers who don't work at home (B08303)
- tax_rate    = aggregate real estate taxes paid (B25090) / aggregate home value (B25082)
  The pre-registered median ratio (B25103 / B25077) is kept as tax_rate_median, but
  B25103 is top-coded at $10,000, which caps it for many high-tax suburbs
  (see the change log in docs/decisions.md).

Output: data/processed/acs.csv
"""
import pandas as pd

from fetch import ROOT, fetch

YEAR = 2024  # 2020-2024 ACS 5-year, the latest release on the pull date
BASE = f"https://www2.census.gov/programs-surveys/acs/summary_file/{YEAR}/table-based-SF/data/5YRData"

# Values the Census uses for top-coded medians ("10,000+" and "2,000,000+")
TAX_TOPCODE = 10001
VALUE_TOPCODE = 2000001


def table(name, cols):
    path = fetch(f"{BASE}/acsdt5y{YEAR}-{name}.dat")
    df = pd.read_csv(path, sep="|", dtype={"GEO_ID": str}, usecols=["GEO_ID", *cols])
    df = df[df.GEO_ID.str.startswith("860Z200US")]
    df["zcta"] = df.GEO_ID.str[-5:]
    return df.set_index("zcta").drop(columns="GEO_ID")


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    df = pd.concat([
        table("b08013", ["B08013_E001"]),
        table("b08303", ["B08303_E001"]),
        table("b25103", ["B25103_E001", "B25103_M001"]),
        table("b25077", ["B25077_E001", "B25077_M001"]),
        table("b25090", ["B25090_E001"]),
        table("b25082", ["B25082_E001"]),
    ], axis=1).loc[lambda d: d.index.isin(zips.zcta)]
    df = df.apply(pd.to_numeric, errors="coerce")
    # Negative values are Census "not available" codes
    df = df.mask(df < 0)

    out = pd.DataFrame(index=df.index)
    out["workers_commuting"] = df.B08303_E001
    out["commute_min"] = df.B08013_E001 / df.B08303_E001
    out["median_tax_paid"] = df.B25103_E001
    out["median_tax_paid_moe"] = df.B25103_M001
    out["median_home_value"] = df.B25077_E001
    out["median_home_value_moe"] = df.B25077_M001
    out["tax_rate"] = df.B25090_E001 / df.B25082_E001
    out["tax_rate_median"] = df.B25103_E001 / df.B25077_E001
    out["median_topcoded"] = (df.B25103_E001 >= TAX_TOPCODE) | (df.B25077_E001 >= VALUE_TOPCODE)
    out = out.reset_index().rename(columns={"index": "zcta"})
    out = zips[["zcta"]].merge(out, on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/acs.csv", index=False, float_format="%.5g")
    print(out.describe().T.to_string())
    print("corr(aggregate, median) where median not top-coded:",
          round(out.loc[~out.median_topcoded, ["tax_rate", "tax_rate_median"]].corr().iloc[0, 1], 3))
    print("missing commute:", out.commute_min.isna().sum(), "| missing tax rate:", out.tax_rate.isna().sum(),
          "| top-coded:", out.median_topcoded.sum())


if __name__ == "__main__":
    main()
