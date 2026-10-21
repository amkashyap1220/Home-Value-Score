"""The value score behind the interactive map on alexanderk.dev (replaces the
regression for the post on 2026-10-21; see the change log in docs/decisions.md).

For every zip, six things are turned into percentile ranks from 0 to 100 within the
sample, so that higher is always better:

  schools, safety, commute, walkability   as in model.py
  newer homes                             median year built (ACS B25035): newer = higher
  low price                               median price per sq ft (buyers) or median gross
                                          rent (renters): cheaper = higher

  quality     = weighted average of the first five (weights 0 to 3; 1 each by default).
                A missing indicator counts as 50, the middle, so a gap in the data neither
                helps nor hurts a zip.
  value score = (1 - price share) x quality + price share x low-price percentile
                (price share 0 to 100%; 50% by default: what you get counts as much as what
                you pay)
  value areas = the 20 highest value scores among zips with above-median quality

Targets (page only): a reader can also set a target for any factor, such as a longest
commute or a budget. A zip that meets the target scores 100 on that factor; one that misses
it scores 100 x its percentile / the target's percentile, so it falls off the further it
misses. For buyers the budget is compared with the median sale price. A second person can
enter their own weights and targets; "best for both" ranks zips by the lower of the two
value scores, among zips above both people's quality medians. None of this changes the
default results this script computes.

The page runs the same steps in the browser (js/chicago-home-value-model.js), so readers can
set their own weights. This script computes the default ("my") results.

Samples:
  buyers   at least 20 sales in the 12-month window (as pre-registered), a price per sq ft,
           at most one missing quality indicator, and a home age
  renters  a median gross rent and at least 100 renter-occupied homes, at most one missing
           quality indicator, and a home age

Outputs: output/value.csv (one row per zip and sample), output/value.json (summary)
"""
import json

import pandas as pd

from fetch import ROOT

P, OUT = ROOT / "data/processed", ROOT / "output"
MIN_SALES, MIN_RENTERS = 20, 100
TOP = 20
# column -> True if higher is better
FACTORS = {"school_pct": True, "crimes_per_1000": False, "commute_min": False, "walk_index": True,
           "home_age": False}
NAMES = ["schools", "safety", "commute", "walkability", "newer_homes"]
PRICE = {"buy": "ppsf", "rent": "rent"}
DEFAULT = {"weights": [1, 1, 1, 1, 1], "price_share": 0.5}


def load():
    df = (pd.read_csv(P / "indicators.csv", dtype={"zcta": str})
          .merge(pd.read_csv(P / "prices.csv", dtype={"zcta": str}), on="zcta", how="left")
          .merge(pd.read_csv(P / "extras.csv", dtype={"zcta": str})[["zcta", "home_age"]], on="zcta", how="left")
          .merge(pd.read_csv(P / "rent.csv", dtype={"zcta": str})[["zcta", "rent", "renter_units"]], on="zcta", how="left"))
    ok = (df.quality_missing < 2) & df.home_age.notna()
    return {
        "buy": df[ok & (df.sales_12m >= MIN_SALES) & df.ppsf.notna()].reset_index(drop=True),
        "rent": df[ok & (df.renter_units >= MIN_RENTERS) & df.rent.notna()].reset_index(drop=True),
    }


def percentiles(df, mode):
    """Percentile ranks within the sample; higher is better for every column."""
    out = pd.DataFrame(index=df.index)
    for (col, higher_better), name in zip(FACTORS.items(), NAMES):
        r = df[col].rank(ascending=higher_better, method="average")
        out[name] = (r - 1) / (r.count() - 1) * 100
    r = df[PRICE[mode]].rank(ascending=False, method="average")
    out["low_price"] = (r - 1) / (r.count() - 1) * 100
    return out


def score(pct, weights, price_share):
    w = pd.Series(weights, index=NAMES, dtype=float)
    quality = (pct[NAMES].fillna(50) * w).sum(axis=1) / w.sum()
    value = (1 - price_share) * quality + price_share * pct.low_price
    area = pd.Series(False, index=pct.index)
    area[value[quality > quality.median()].nlargest(TOP).index] = True
    return quality, value, area


def main():
    rows, summary = [], {"default": DEFAULT, "top": TOP}
    for mode, df in load().items():
        pct = percentiles(df, mode)
        quality, value, area = score(pct, **DEFAULT)
        res = df[["zcta", "place_name", "state", "county", "on_list", "list_entry", *FACTORS, PRICE[mode], "median_price"]].rename(
            columns={PRICE[mode]: "price"}).join(pct.round(3))
        if mode == "rent":
            res["median_price"] = None
        res["quality"], res["value"], res["value_area"] = quality, value, area
        res["rank"] = value.rank(ascending=False, method="min").astype(int)
        res.insert(0, "mode", mode)
        rows.append(res)

        top = res[res.value_area].sort_values("value", ascending=False)
        listed = res[res.on_list]
        summary[mode] = {
            "n": len(res),
            "quality_median": round(quality.median(), 2),
            "value_areas": top.zcta.tolist(),
            "on_list": int(top.on_list.sum()),
            "on_list_entries": top[top.on_list].list_entry.tolist(),
            "illinois": int((top.state == "IL").sum()),
            "list_zips": len(listed),
            "list_median_rank": float(listed["rank"].median()),
            "list_median_quality": round(listed.quality.median(), 1),
            "other_median_quality": round(res[~res.on_list].quality.median(), 1),
            "list_median_price": round(listed.price.median(), 2),
            "other_median_price": round(res[~res.on_list].price.median(), 2),
        }
        # Niche's Illinois list against the other Illinois zips
        il = res[res.state == "IL"]
        summary[mode]["illinois_list"] = {
            "zips": int(il.on_list.sum()),
            "in_value_areas": int((il.on_list & il.value_area).sum()),
            "median_rank": float(il[il.on_list]["rank"].median()),
            "median_quality": round(il[il.on_list].quality.median(), 1),
            "other_median_quality": round(il[~il.on_list].quality.median(), 1),
            "median_price": round(il[il.on_list].price.median(), 2),
            "other_median_price": round(il[~il.on_list].price.median(), 2),
        }
        print(f"\n== {mode}: n={len(res)}, {summary[mode]['on_list']} of {TOP} value areas on the Niche list "
              f"({', '.join(summary[mode]['on_list_entries']) or 'none'}); {summary[mode]['illinois']} in Illinois")
        print(top[["zcta", "place_name", "state", "price", "quality", "value", "on_list"]].round(1).to_string(index=False))
        print({k: v for k, v in summary[mode].items() if k.startswith(("list", "other", "illinois_"))})

    pd.concat(rows).to_csv(OUT / "value.csv", index=False, float_format="%.4g")
    (OUT / "value.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
