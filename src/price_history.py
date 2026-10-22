"""Price per square foot for earlier 12-month windows and for single-family homes only,
from the same Redfin file as src/prices.py (added 2026-10-22).

Used by src/value_gap.py for two checks of the housing value model, not for the scores:

- persistence: is a zip that sells below its expected price this year also below it in
  earlier years? A gap that flips sign from year to year is mostly noise.
- property type: does the gap hold when only single-family homes are counted? Redfin's
  "All Residential" median mixes condos and houses, which have very different prices
  per sq ft.

Each window is 12 months ending in May (the latest window ends 2026-05-31, as in
prices.py), built the same way: the homes-sold-weighted average of the medians of the
four non-overlapping 90-day periods. The 2026 "All Residential" window reproduces
data/processed/prices.csv.

Output: data/processed/price_history.csv
  zcta, property_type ("all" or "single_family"), window_end, ppsf, median_price, sales
"""
import duckdb
import pandas as pd

from fetch import ROOT, fetch
from prices import REDFIN

TYPES = {"All Residential": "all", "Single Family Residential": "single_family"}
FIRST_YEAR, LAST_YEAR = 2019, 2026


def windows(df, last):
    """The four 90-day period ends that make up the 12 months ending on `last`."""
    return [last - pd.offsets.MonthEnd(3 * k) for k in range(4)]


def summarize(w):
    w = w.assign(sold=w.sold.fillna(0))
    priced = w.dropna(subset=["ppsf"])
    wavg = lambda col: priced.groupby("zcta").apply(
        lambda g: (g[col] * g.sold).sum() / g.sold.sum() if g.sold.sum() else None, include_groups=False)
    return pd.DataFrame({"ppsf": wavg("ppsf"), "median_price": wavg("median_price"),
                         "sales": w.groupby("zcta").sold.sum()})


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    path = fetch(REDFIN)
    duckdb.sql("set enable_progress_bar = false")
    types = ", ".join(f"'{t}'" for t in TYPES)
    df = duckdb.sql(f"""
        select right(REGION, 5) as zcta, PROPERTY_TYPE as property_type, PERIOD_END as period_end,
               MEDIAN_PPSF as ppsf, HOMES_SOLD as sold, MEDIAN_SALE_PRICE as median_price
        from read_csv('{path}', delim='\t', header=true, nullstr='NA')
        where STATE_CODE in ('IL', 'IN') and PROPERTY_TYPE in ({types})
          and PERIOD_DURATION = 90 and not IS_SEASONALLY_ADJUSTED
    """).df()
    df = df[df.zcta.isin(set(zips.zcta))]
    df["period_end"] = pd.to_datetime(df.period_end)
    out = []
    for ptype, short in TYPES.items():
        d = df[df.property_type == ptype]
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            last = pd.Timestamp(f"{year}-05-31")
            s = summarize(d[d.period_end.isin(windows(d, last))])
            out.append(s.assign(property_type=short, window_end=last.date().isoformat()).reset_index(names="zcta"))
    out = pd.concat(out)[["zcta", "property_type", "window_end", "ppsf", "median_price", "sales"]]
    out["sales"] = out.sales.astype(int)
    out.to_csv(ROOT / "data/processed/price_history.csv", index=False, float_format="%.5g")
    print(out.groupby(["property_type", "window_end"]).agg(zips=("zcta", "size"), median_ppsf=("ppsf", "median"),
                                                           sales=("sales", "sum")).to_string())


if __name__ == "__main__":
    main()
