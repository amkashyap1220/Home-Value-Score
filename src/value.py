"""The target score behind the interactive map on alexanderk.dev (replaces the
weighted value score on 2026-10-21; see the change log in docs/decisions.md).

A reader sets a target and a weight for each of six factors:

  schools       district proficiency percentile within the state (0 to 100)
  safety        crimes per 1,000 residents a year
  commute       average one-way commute, minutes (ACS); or, when the reader names a
                workplace zip, the drive time from each zip to it (src/commute.py)
  walkability   EPA National Walkability Index (1 to 20)
  home age      median age of the homes, years (ACS B25035)
  price         median sale price (buyers, Redfin) or median gross rent a month (renters, ACS B25064)

How close a zip is to a target is measured in percentile points, so that minutes,
dollars and crime rates are comparable:

  pct(x)      = share of the sample's zips below x (ties count half), 0 to 100
  closeness   = 100 - |pct(zip's value) - pct(target)|
                100 when the zip is exactly on target, lower the further away it is.
                For schools, safety and price, doing better than the target (better schools,
                less crime, a lower price) also counts as 100; for the other three, being off
                in either direction lowers it. A missing value counts as 50.
  score       = sum(weight x closeness) / sum(weight)
  top areas   = the 20 highest scores

Two people: each gets their own score; "best for both" ranks by the lower of the two.

The page runs the same steps in the browser (js/chicago-home-value-model.js). SAMPLE below
(typical targets, every weight Normal, a job in the Loop) is what the page fills in on load
and what its "Use sample values" button restores, so its output can be checked against the
page. The same targets without a workplace (the Census average commute) are a second check.

Samples:
  buyers   at least 20 sales in the 12-month window (as pre-registered), a median sale
           price, at most one missing quality indicator, and a home age
  renters  a median gross rent and at least 100 renter-occupied homes, at most one missing
           quality indicator, and a home age

Outputs: output/value.csv (one row per zip and sample, sample scores), output/value.json
"""
import json

import pandas as pd

from fetch import ROOT

P, OUT = ROOT / "data/processed", ROOT / "output"
MIN_SALES, MIN_RENTERS = 20, 100
TOP = 20
NAMES = ["schools", "safety", "commute", "walkability", "home_age", "price"]
COLUMNS = {"buy": ["school_pct", "crimes_per_1000", "commute_min", "walk_index", "home_age", "median_price"],
           "rent": ["school_pct", "crimes_per_1000", "commute_min", "walk_index", "home_age", "rent"]}
# Which way is "better than the target": +1 higher is better, -1 lower is better, 0 no better side
DIRECTION = [1, -1, 0, 0, 0, -1]
# Sample values the page starts with: round numbers near each sample's medians, every
# weight Normal, and a job in the Loop (60606)
SAMPLE = {
    "buy": {"targets": [50, 11, 30, 11, 50, 350000], "weights": [1, 1, 1, 1, 1, 1], "workplace": "60606"},
    "rent": {"targets": [50, 11, 30, 11, 50, 1400], "weights": [1, 1, 1, 1, 1, 1], "workplace": "60606"},
}


def load():
    df = (pd.read_csv(P / "indicators.csv", dtype={"zcta": str})
          .merge(pd.read_csv(P / "prices.csv", dtype={"zcta": str}), on="zcta", how="left")
          .merge(pd.read_csv(P / "extras.csv", dtype={"zcta": str})[["zcta", "home_age"]], on="zcta", how="left")
          .merge(pd.read_csv(P / "rent.csv", dtype={"zcta": str})[["zcta", "rent", "renter_units"]], on="zcta", how="left"))
    ok = (df.quality_missing < 2) & df.home_age.notna()
    return {
        "buy": df[ok & (df.sales_12m >= MIN_SALES) & df.median_price.notna()].reset_index(drop=True),
        "rent": df[ok & (df.renter_units >= MIN_RENTERS) & df.rent.notna()].reset_index(drop=True),
    }


def pct(values, x):
    """Share of the known values below x, ties counting half, as 0 to 100."""
    v = values.dropna()
    return ((v < x).sum() + (v == x).sum() / 2) / len(v) * 100


def drive_to(df, workplace):
    """Whole-minute drive times from each zip to the workplace zip, as the site stores them."""
    m = pd.read_csv(P / "drive_minutes.csv", dtype={"from": str}).set_index("from")
    return df.zcta.map(m[workplace]).round().clip(upper=255)


def score(df, mode, targets, weights, workplace=None):
    cols = COLUMNS[mode]
    if workplace:
        df = df.assign(commute_min=drive_to(df, workplace))
    close = pd.DataFrame(index=df.index)
    for name, col, t, sign in zip(NAMES, cols, targets, DIRECTION):
        gap = df[col].map(lambda x: pct(df[col], x) if pd.notna(x) else None) - pct(df[col], t)
        if sign:
            gap = gap.where(gap * sign < 0, 0)   # better than the target counts as on target
        close[name] = (100 - gap.abs()).fillna(50)
    w = pd.Series(weights, index=NAMES, dtype=float)
    return close, (close * w).sum(axis=1) / w.sum()


def main():
    rows, summary = [], {"top": TOP, "sample": SAMPLE}
    for mode, df in load().items():
        ex = SAMPLE[mode]
        close, s = score(df, mode, ex["targets"], ex["weights"], ex["workplace"])
        res = df[["zcta", "place_name", "state", "county", "on_list", "list_entry", *COLUMNS[mode]]].rename(
            columns={COLUMNS[mode][-1]: "price"})
        res = res.join(close.add_prefix("close_").round(2))
        res["score"] = s.round(2)
        res["rank"] = s.rank(ascending=False, method="min").astype(int)
        res["top"] = res["rank"] <= TOP
        res.insert(0, "mode", mode)
        rows.append(res)

        top = res.sort_values("score", ascending=False).head(TOP)
        summary[mode] = {
            "n": len(res),
            "top": top.zcta.tolist(),
            "top_scores": top.score.tolist(),
            "on_list": int(top.on_list.sum()),
        }
        _, s_census = score(df, mode, ex["targets"], ex["weights"])
        census = df.assign(score=s_census.round(2)).sort_values("score", ascending=False).head(TOP)
        summary[mode]["no_workplace"] = {"top": census.zcta.tolist(), "top_scores": census.score.tolist()}
        print(f"\n== {mode}, no workplace (Census commute): " + ", ".join(f"{z} {v}" for z, v in zip(census.zcta[:5], census.score[:5])))
        print(f"\n== {mode}: n={len(res)}, sample targets {ex['targets']}, working in {ex['workplace']}; "
              f"{summary[mode]['on_list']} of the top {TOP} on the Niche list")
        print(top[["zcta", "place_name", "state", "price", "score", "on_list"]].to_string(index=False))

    pd.concat(rows).to_csv(OUT / "value.csv", index=False, float_format="%.6g")
    (OUT / "value.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
