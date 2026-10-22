"""The target score behind the interactive map on alexanderk.dev (replaces the
weighted value score on 2026-10-21; see the change log in docs/decisions.md).

A reader sets a target and a weight for each of seven factors:

  schools       district proficiency percentile within the state (0 to 100)
  safety        crimes per 1,000 residents a year (the police agency's rate; inside Chicago, the
                zip's own rate from src/chicago_crime.py, since 2026-10-22)
  commute       average one-way commute, minutes (ACS); or, when the reader names a
                workplace zip, the drive time from each zip to it (src/commute.py)
  walkability   EPA National Walkability Index (1 to 20)
  home age      median age of the homes, years (ACS B25035)
  price         median sale price (buyers, Redfin) or rent per person a month (renters: median gross
                rent, ACS B25064, divided by the average bedrooms of rented homes, B25042)
  train         straight-line miles from where people live to the nearest Metra, CTA 'L' or
                South Shore Line station (src/stations.py; added 2026-10-22)

How close a zip is to a target is measured in percentile points, so that minutes,
dollars and crime rates are comparable:

  pct(x)      = share of the sample's zips below x (ties count half), 0 to 100
  closeness   = 100 - |pct(zip's value) - pct(target)|
                100 when the zip is exactly on target, lower the further away it is.
                For schools, safety, price and train, doing better than the target (better
                schools, less crime, a lower price, a closer station) also counts as 100; for the
                other three, being off in either direction lowers it.
  score       = sum(weight x closeness) / sum(weight), over the factors the zip has data for
  coverage    = sum(weight of the factors it has data for) / sum(weight)
  top areas   = the 20 highest scores among zips with coverage of at least 80%

Missing data (since 2026-10-22): a missing value used to count as 50, which quietly
treated an unknown as average. Now the score uses only measured factors, the coverage
says how much of the reader's weight that is, and a zip whose missing factors carry more
than 20% of the weight is shown but not ranked. With the sample weights (safety at Top),
a zip with no crime data is never ranked.

Two people: each gets their own score; "best for both" ranks by the lower of the two.

The page runs the same steps in the browser (js/chicago-home-value-model.js). SAMPLE below
(strong schools and safety, a job in the Loop) is what the page fills in on load
and what its "Use sample values" button restores, so its output can be checked against the
page. The same targets without a workplace (the Census average commute) are a second check.

Samples:
  buyers   at least 20 sales in the 12-month window (as pre-registered), a median sale
           price, at most one missing quality indicator, and a home age
  renters  a rent per person and at least 100 renter-occupied homes, at most one missing
           quality indicator, and a home age

Outputs: output/value.csv (one row per zip and sample, sample scores), output/value.json
"""
import base64
import json

import numpy as np
import pandas as pd

from fetch import ROOT

P, OUT = ROOT / "data/processed", ROOT / "output"
MIN_SALES, MIN_RENTERS = 20, 100
TOP = 20
NAMES = ["schools", "safety", "commute", "walkability", "home_age", "price", "train"]
COLUMNS = {"buy": ["school_pct", "crimes_per_1000_local", "commute_min", "walk_index", "home_age", "median_price", "station_mi"],
           "rent": ["school_pct", "crimes_per_1000_local", "commute_min", "walk_index", "home_age", "rent_per_person", "station_mi"]}
MIN_COVERAGE = 0.8   # share of the reader's weight that must be measured for a zip to be ranked
# Which way is "better than the target": +1 higher is better, -1 lower is better, 0 no better side
DIRECTION = [1, -1, 0, 0, 0, -1, -1]
# Sample values the page starts with: schools and safety at Top, commute, home age and train at Low,
# the rest Normal, a job in the Loop (60606)
SAMPLE = {
    "buy": {"targets": [90, 11, 30, 10, 30, 600000, 2], "weights": [3, 3, 0.5, 1, 0.5, 1, 0.5], "workplace": "60606"},
    "rent": {"targets": [90, 11, 30, 10, 30, 1200, 2], "weights": [3, 3, 0.5, 1, 0.5, 1, 0.5], "workplace": "60606"},
}


def load():
    df = (pd.read_csv(P / "indicators.csv", dtype={"zcta": str})
          .merge(pd.read_csv(P / "prices.csv", dtype={"zcta": str}), on="zcta", how="left")
          .merge(pd.read_csv(P / "extras.csv", dtype={"zcta": str})[["zcta", "home_age"]], on="zcta", how="left")
          .merge(pd.read_csv(P / "rent.csv", dtype={"zcta": str})[["zcta", "rent_per_person", "renter_units"]], on="zcta", how="left")
          .merge(pd.read_csv(P / "station_distance.csv", dtype={"zcta": str})[["zcta", "station_mi"]], on="zcta", how="left"))
    # The page gets every value rounded to 2 decimals (src/site_data.py); score the same numbers so the two match
    cols = sorted({c for v in COLUMNS.values() for c in v})
    df[cols] = df[cols].round(2)
    ok = (df.quality_missing < 2) & df.home_age.notna()
    return {
        "buy": df[ok & (df.sales_12m >= MIN_SALES) & df.median_price.notna()].reset_index(drop=True),
        "rent": df[ok & (df.renter_units >= MIN_RENTERS) & df.rent_per_person.notna()].reset_index(drop=True),
    }


def pct(values, x):
    """Share of the known values below x, ties counting half, as 0 to 100."""
    v = values.dropna()
    if v.empty:
        return np.nan
    return ((v < x).sum() + (v == x).sum() / 2) / len(v) * 100


def drive_to(df, workplace):
    """Whole-minute drive times from each zip to the workplace zip, read from the file the site uses
    (rounding the one-decimal CSV again could differ by a minute)."""
    t = json.loads((OUT / "site/chicago-home-value-drive.json").read_text())
    grid = np.frombuffer(base64.b64decode(t["minutes"]), dtype=np.uint8).reshape(len(t["zips"]), -1)
    col = pd.Series(grid[:, t["zips"].index(workplace)].astype(float), index=t["zips"])
    return df.zcta.map(col)


def score(df, mode, targets, weights, workplace=None):
    cols = COLUMNS[mode]
    if workplace:
        df = df.assign(commute_min=drive_to(df, workplace))
    close = pd.DataFrame(index=df.index)
    for name, col, t, sign in zip(NAMES, cols, targets, DIRECTION):
        gap = df[col].map(lambda x: pct(df[col], x) if pd.notna(x) else None) - pct(df[col], t)
        if sign:
            gap = gap.where((gap * sign < 0) | gap.isna(), 0)   # better than the target counts as on target
        close[name] = 100 - gap.abs()                            # NaN when the zip has no value
    w = pd.Series(weights, index=NAMES, dtype=float)
    measured = close.notna() * w
    coverage = measured.sum(axis=1) / w.sum()
    s = (close.fillna(0) * w).sum(axis=1) / measured.sum(axis=1)
    return close, s.where(measured.sum(axis=1) > 0), coverage


def top(scores, coverage, n=TOP):
    """The n highest scores among zips with enough coverage; ties keep the input order (by zip)."""
    return scores[coverage >= MIN_COVERAGE - 1e-9].sort_values(ascending=False, kind="stable").head(n)


def main():
    rows, summary = [], {"top": TOP, "min_coverage": MIN_COVERAGE, "sample": SAMPLE}
    for mode, df in load().items():
        ex = SAMPLE[mode]
        close, s, cov = score(df, mode, ex["targets"], ex["weights"], ex["workplace"])
        res = df[["zcta", "place_name", "state", "county", *COLUMNS[mode]]].rename(
            columns={COLUMNS[mode][5]: "price"})
        res = res.join(close.add_prefix("close_").round(2))
        res["score"] = s.round(2)
        res["coverage"] = cov.round(3)
        res["ranked"] = cov >= MIN_COVERAGE - 1e-9
        best = top(s, cov)
        res["top"] = res.index.isin(best.index)
        res.insert(0, "mode", mode)
        rows.append(res)

        best = res.loc[best.index]
        summary[mode] = {
            "n": len(res),
            "unranked": int((~res.ranked).sum()),
            "top": best.zcta.tolist(),
            "top_scores": best.score.tolist(),
        }
        _, s_census, cov_census = score(df, mode, ex["targets"], ex["weights"])
        census = df.loc[top(s_census, cov_census).index].assign(score=s_census.round(2))
        summary[mode]["no_workplace"] = {"top": census.zcta.tolist(), "top_scores": census.score.tolist()}
        print(f"\n== {mode}, no workplace (Census commute): " + ", ".join(f"{z} {v}" for z, v in zip(census.zcta[:5], census.score[:5])))
        print(f"\n== {mode}: n={len(res)}, sample targets {ex['targets']}, working in {ex['workplace']}; "
              f"top {TOP}")
        print(best[["zcta", "place_name", "state", "price", "score", "coverage"]].to_string(index=False))

    pd.concat(rows).to_csv(OUT / "value.csv", index=False, float_format="%.6g")
    (OUT / "value.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
