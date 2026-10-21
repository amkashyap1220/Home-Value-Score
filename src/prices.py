"""12-month price per square foot and sales count by zip, from the Redfin Data Center
zip code market tracker ("All Residential").

Redfin publishes zip data as rolling 90-day periods ending each month. The 12-month
window is covered by the four non-overlapping periods ending on the latest period end
and 3, 6 and 9 months before it. Price per sq ft is the homes-sold-weighted average of
their medians (pre-registered approximation of a 12-month median); sales are summed.

Zillow ZHVI is added as context only (1-year change in typical home value).

Output: data/processed/prices.csv
"""
import duckdb
import pandas as pd

from fetch import ROOT, fetch

REDFIN = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz"
ZHVI = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"


def redfin(zctas):
    path = fetch(REDFIN)
    df = duckdb.sql(f"""
        select right(REGION, 5) as zcta, PERIOD_END as period_end, MEDIAN_PPSF as ppsf,
               HOMES_SOLD as sold, MEDIAN_SALE_PRICE as median_price
        from read_csv('{path}', delim='\t', header=true, nullstr='NA')
        where STATE_CODE in ('IL', 'IN') and PROPERTY_TYPE = 'All Residential'
          and PERIOD_DURATION = 90 and not IS_SEASONALLY_ADJUSTED
    """).df()
    df = df[df.zcta.isin(zctas)]
    last = df.period_end.max()
    ends = [last - pd.offsets.MonthEnd(3 * k) for k in range(4)]
    w = df[df.period_end.isin(ends)].copy()
    w["sold"] = w.sold.fillna(0)
    priced = w.dropna(subset=["ppsf"])
    out = pd.DataFrame({
        "sales_12m": w.groupby("zcta").sold.sum(),
        "periods": w.groupby("zcta").period_end.nunique(),
        "ppsf": priced.groupby("zcta").apply(lambda g: (g.ppsf * g.sold).sum() / g.sold.sum() if g.sold.sum() else None),
        "median_price": priced.groupby("zcta").apply(lambda g: (g.median_price * g.sold).sum() / g.sold.sum() if g.sold.sum() else None),
    })
    start = (ends[-1] - pd.offsets.MonthBegin(3)).date()
    print(f"Redfin window: {start} to {last.date()} (periods ending {[e.date().isoformat() for e in ends]})")
    return out.reset_index(names="zcta"), (start, last.date())


def zhvi(zctas):
    z = pd.read_csv(fetch(ZHVI), dtype={"RegionName": str}).copy()
    z["zcta"] = z.RegionName.str.zfill(5)
    z = z[z.zcta.isin(zctas)].set_index("zcta")
    months = [c for c in z.columns if c[:2] == "20"]
    last = months[-1]
    return pd.DataFrame({"zhvi": z[last], "zhvi_1y_change": z[last] / z[months[-13]] - 1}).reset_index(), last


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    r, window = redfin(set(zips.zcta))
    z, zmonth = zhvi(set(zips.zcta))
    out = zips[["zcta"]].merge(r, on="zcta", how="left").merge(z, on="zcta", how="left")
    out["sales_12m"] = out.sales_12m.fillna(0).astype(int)
    out.to_csv(ROOT / "data/processed/prices.csv", index=False, float_format="%.5g")
    print(f"ZHVI month: {zmonth}")
    print(out.describe().T.to_string())
    print("zips with >= 20 sales:", (out.sales_12m >= 20).sum())


if __name__ == "__main__":
    main()
