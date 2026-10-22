"""Join the step-2 inputs into one table per zip: the four quality indicators (raw
values, before percentiles), the tax rate and the place name.

Percentile ranks and the quality score are computed in step 3, after the sales
filter, because the pre-registration ranks zips within the final sample.

crimes_per_1000 is the pre-registered agency rate (one rate per police agency), which
src/model.py keeps using. crimes_per_1000_local (added 2026-10-22) is the same except in
Chicago, where it is the zip's own rate from src/chicago_crime.py; the map's fit score and
the housing value model (src/value.py, src/value_gap.py) use it.

Output: data/processed/indicators.csv
"""
import pandas as pd

from fetch import ROOT

P = ROOT / "data/processed"


def main():
    read = lambda name: pd.read_csv(P / name, dtype={"zcta": str})
    df = (read("zips.csv")
          .merge(read("schools.csv")[["zcta", "school_pct"]], on="zcta", how="left")
          .merge(read("crime.csv")[["zcta", "agency_name", "crime_year", "crimes_per_1000", "note"]]
                 .rename(columns={"agency_name": "police_agency", "note": "crime_note"}),
                 on="zcta", how="left")
          .merge(read("acs.csv")[["zcta", "commute_min", "tax_rate", "tax_rate_median", "median_topcoded"]], on="zcta", how="left")
          .merge(read("walkability.csv"), on="zcta", how="left")
          .merge(read("places.csv")[["zcta", "place_name"]], on="zcta", how="left")
          .merge(read("chicago_crime.csv")[["zcta", "crimes_per_1000_local"]], on="zcta", how="left"))
    df["crimes_per_1000_local"] = df.crimes_per_1000_local.fillna(df.crimes_per_1000)
    quality = ["school_pct", "crimes_per_1000", "commute_min", "walk_index"]
    df["quality_missing"] = df[quality].isna().sum(axis=1)
    df.to_csv(P / "indicators.csv", index=False, float_format="%.5g")

    print(df[quality + ["tax_rate"]].notna().sum().to_string())
    print("zips missing 0/1/2+ quality indicators:", df.quality_missing.value_counts().sort_index().to_dict())
    print(df[(df.quality_missing > 0) | df.tax_rate.isna()][["zcta", "place_name", "pop2020", *quality, "tax_rate"]].to_string(index=False))


if __name__ == "__main__":
    main()
