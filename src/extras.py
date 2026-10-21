"""Post-hoc controls added at Alex's request on 2026-10-21, after the pre-registered
results were seen (see the change log in docs/decisions.md):

- home_age            years since the median year built (ACS B25035; "1939 or earlier" is published as one value, 1938)
- home_energy_month   estimated mean monthly electricity + home gas bill, among homes billed
                      for each (ACS B25132, B25133; bin midpoints, top bins set to $300 / $175)
- commute_fuel_year   estimated yearly gasoline cost of commuting per worker:
                      share of workers who drive x mean one-way commute minutes x 2 trips x 250 days
                      x 30 mph / 25 mpg x the average pump price over the price window
                      (EIA weekly regular gasoline: Chicago for Illinois zips, Midwest for Indiana zips;
                      EIA has no Indiana or NW Indiana series)

Output: data/processed/extras.csv
"""
import pandas as pd

from acs import table
from fetch import ROOT, fetch

EIA = "https://www.eia.gov/dnav/pet/hist_xls/{series}w.xls"
GAS_SERIES = {"IL": "EMM_EPMR_PTE_YORD_DPG", "IN": "EMM_EPMR_PTE_R20_DPG"}  # Chicago, Midwest (PADD 2)
WINDOW = ("2025-06-01", "2026-05-31")  # same as the Redfin price window
YEAR_NOW = 2026
MPH, MPG, WORKDAYS = 30, 25, 250

ELECTRIC_BINS = {"B25132_E004": 25, "B25132_E005": 75, "B25132_E006": 125, "B25132_E007": 175,
                 "B25132_E008": 225, "B25132_E009": 300}
GAS_BINS = {"B25133_E004": 12.5, "B25133_E005": 37.5, "B25133_E006": 62.5, "B25133_E007": 87.5,
            "B25133_E008": 125, "B25133_E009": 175}


def gas_price(state):
    df = pd.read_excel(fetch(EIA.format(series=GAS_SERIES[state])), sheet_name="Data 1", skiprows=2)
    df.columns = ["date", "price"]
    df = df[(df.date >= WINDOW[0]) & (df.date <= WINDOW[1])]
    return df.price.mean()


def binned_mean(df, bins):
    counts = df[list(bins)]
    return (counts * pd.Series(bins)).sum(axis=1) / counts.sum(axis=1)


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    acs = pd.read_csv(ROOT / "data/processed/acs.csv", dtype={"zcta": str}).set_index("zcta")
    df = pd.concat([
        table("b25035", ["B25035_E001"]),
        table("b25132", list(ELECTRIC_BINS)),
        table("b25133", list(GAS_BINS)),
        table("b08301", ["B08301_E001", "B08301_E002", "B08301_E021"]),
    ], axis=1).loc[lambda d: d.index.isin(zips.zcta)].apply(pd.to_numeric, errors="coerce")
    df = df.mask(df < 0)

    prices = {s: gas_price(s) for s in GAS_SERIES}
    out = pd.DataFrame(index=df.index)
    out["median_year_built"] = df.B25035_E001
    out["home_age"] = YEAR_NOW - df.B25035_E001
    out["electric_month"] = binned_mean(df, ELECTRIC_BINS)
    out["home_gas_month"] = binned_mean(df, GAS_BINS)
    out["home_energy_month"] = out.electric_month + out.home_gas_month
    commuters = df.B08301_E001 - df.B08301_E021  # workers minus those working from home
    out["drive_share"] = df.B08301_E002 / commuters
    state = out.index.map(zips.set_index("zcta").state)
    out["pump_price"] = state.map(prices)
    miles_year = acs.commute_min.reindex(out.index) / 60 * MPH * 2 * WORKDAYS
    out["commute_fuel_year"] = out.drive_share * miles_year / MPG * out.pump_price
    out = zips[["zcta"]].merge(out.reset_index(names="zcta"), on="zcta", how="left")
    out.to_csv(ROOT / "data/processed/extras.csv", index=False, float_format="%.5g")
    print("pump prices over the window:", {k: round(v, 3) for k, v in prices.items()})
    print(out.describe().T.round(2).to_string())


if __name__ == "__main__":
    main()
