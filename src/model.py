"""Step 3: quality score, value model, value picks and the decision, plus the
robustness checks. Every threshold here comes from docs/decisions.md.

The main model controls for the property tax rate and for running costs and home age
(home_age, home_energy_month, commute_fuel_year from extras.py). Those three were added
on 2026-10-21 after a first run without them, and made the main model at Alex's request
(see the change log in docs/decisions.md). The first run is still computed and saved.

Outputs:
  output/scores.csv, output/scores.json  final table for the site
  output/excluded_zips.csv               dropped zips and why
  output/model_summary.txt               regression output for the main model and the first run
  output/robustness.json                 Illinois-only and drop-one-indicator results
  output/first_run.json                  the first run: quality + tax rate only
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from fetch import ROOT

P, OUT = ROOT / "data/processed", ROOT / "output"
MIN_SALES = 20
# indicator -> True if higher is better
INDICATORS = {"school_pct": True, "crimes_per_1000": False, "commute_min": False, "walk_index": True}
LABELS = {"school_pct": "schools", "crimes_per_1000": "safety", "commute_min": "commute", "walk_index": "walkability"}


# Running costs and home age (made by extras.py)
CONTROLS = ["home_age", "home_energy_month", "commute_fuel_year"]


def sample():
    ind = pd.read_csv(P / "indicators.csv", dtype={"zcta": str})
    prices = pd.read_csv(P / "prices.csv", dtype={"zcta": str})
    extras = pd.read_csv(P / "extras.csv", dtype={"zcta": str})[["zcta", *CONTROLS]]
    df = ind.merge(prices, on="zcta", how="left").merge(extras, on="zcta", how="left")
    reasons = pd.Series("", index=df.index)
    for mask, why in [
        (df.sales_12m < MIN_SALES, f"fewer than {MIN_SALES} sales in the 12-month window"),
        (df.ppsf.isna(), "no price per sq ft"),
        (df.tax_rate.isna(), "no tax rate"),
        (df.quality_missing >= 2, "missing two or more quality indicators"),
        (df[CONTROLS].isna().any(axis=1), "no home age or running-cost data"),
    ]:
        reasons[mask] = reasons[mask] + "; " + why
    df["exclusion"] = reasons.str.lstrip("; ")
    excluded = df[df.exclusion != ""][["zcta", "place_name", "state", "county", "pop2020", "sales_12m", "exclusion"]]
    return df[df.exclusion == ""].drop(columns="exclusion").reset_index(drop=True), excluded


def run(df, indicators=INDICATORS, controls=CONTROLS):
    """Percentiles within this sample, quality score, OLS, residuals and value picks."""
    df = df.copy()
    for col, higher_better in indicators.items():
        r = df[col].rank(ascending=higher_better, method="average")
        df[f"p_{LABELS[col]}"] = (r - 1) / (r.count() - 1) * 100
    pcols = [f"p_{LABELS[c]}" for c in indicators]
    df["quality"] = df[pcols].mean(axis=1)
    df["quality_flag"] = df[pcols].isna().any(axis=1)
    fit = smf.ols(" + ".join(["ppsf ~ quality", "tax_rate", *controls]), data=df).fit()
    df["predicted"] = fit.fittedvalues
    df["residual"] = df.ppsf - df.predicted
    sd = df.residual.std(ddof=1)
    df["residual_sd"] = df.residual / sd
    df["high_quality"] = df.quality > df.quality.median()
    df["underpriced"] = df.residual < -sd
    df["value_pick"] = df.high_quality & df.underpriced
    return df, fit, sd


def decide(df):
    picks = df[df.value_pick]
    off_list = int((~picks.on_list).sum())
    supported = len(picks) >= 3 and off_list > len(picks) / 2
    return {"value_picks": len(picks), "not_on_list": off_list, "h1_supported": bool(supported),
            "zips": picks.sort_values("residual").zcta.tolist()}


def main():
    OUT.mkdir(exist_ok=True)
    df, excluded = sample()
    excluded.to_csv(OUT / "excluded_zips.csv", index=False)
    main_df, fit, sd = run(df)
    result = decide(main_df)
    (OUT / "model_summary.txt").write_text(
        f"Main test: {len(main_df)} zips, residual SD = {sd:.2f} $/sqft\n\n{fit.summary()}\n")

    # Robustness 1: Illinois only (full rerun)
    il_df, il_fit, _ = run(df[df.state == "IL"])
    # Robustness 2: drop one indicator at a time
    drop = {}
    for col in INDICATORS:
        d, _, _ = run(df, {k: v for k, v in INDICATORS.items() if k != col})
        drop[LABELS[col]] = d.set_index("zcta").value_pick
    drop_df = pd.DataFrame(drop)
    main_df["dropone_runs_as_pick"] = main_df.zcta.map(drop_df.sum(axis=1)).astype(int)
    main_df["robust_pick"] = main_df.value_pick & (main_df.dropone_runs_as_pick >= 3)
    main_df["il_only_pick"] = main_df.zcta.map(il_df.set_index("zcta").value_pick)

    robustness = {
        "illinois_only": {**decide(il_df), "n": len(il_df), "r2": il_fit.rsquared},
        "drop_one": {k: {"value_picks": int(v.sum()), "zips": v[v].index.tolist()} for k, v in drop.items()},
        "robust_picks": main_df[main_df.robust_pick].zcta.tolist(),
    }
    (OUT / "robustness.json").write_text(json.dumps(robustness, indent=2, default=float))

    # The first run, before the running-cost controls were added: same sample, quality + tax rate only
    first_df, first_fit, first_sd = run(df, controls=())
    main_df["first_run_pick"] = main_df.zcta.map(first_df.set_index("zcta").value_pick)
    main_df["first_run_residual"] = main_df.zcta.map(first_df.set_index("zcta").residual)
    first = {**decide(first_df), "n": len(first_df), "r2": first_fit.rsquared, "residual_sd": first_sd,
             "coefficients": first_fit.params.to_dict(), "std_errors": first_fit.bse.to_dict(),
             "p_values": first_fit.pvalues.to_dict()}
    (OUT / "first_run.json").write_text(json.dumps(first, indent=2, default=float))
    with open(OUT / "model_summary.txt", "a") as f:
        f.write(f"\n\nFirst run, without running costs and home age: {len(first_df)} zips\n\n{first_fit.summary()}\n")

    cols = ["zcta", "place_name", "state", "county", "sales_12m", "ppsf", "predicted", "residual", "residual_sd",
            "quality", "p_schools", "p_safety", "p_commute", "p_walkability", "quality_flag", "tax_rate",
            "high_quality", "underpriced", "value_pick", "robust_pick", "il_only_pick", "dropone_runs_as_pick",
            "first_run_pick", "first_run_residual", *CONTROLS,
            "on_list", "list_entry", "median_price", "zhvi_1y_change", "school_pct", "crimes_per_1000",
            "crime_year", "commute_min", "walk_index"]
    scores = main_df[cols].sort_values("residual")
    scores.to_csv(OUT / "scores.csv", index=False, float_format="%.4g")
    site = scores[["zcta", "place_name", "state", "ppsf", "predicted", "residual", "quality", "tax_rate",
                   "value_pick", "first_run_pick", "on_list", "list_entry"]].round({"ppsf": 1, "predicted": 1, "residual": 1, "quality": 1, "tax_rate": 4})
    meta = {"n": len(main_df), "coefficients": fit.params.to_dict(), "std_errors": fit.bse.to_dict(),
            "p_values": fit.pvalues.to_dict(), "r2": fit.rsquared, "residual_sd": sd,
            "quality_median": main_df.quality.median(), **result}
    (OUT / "scores.json").write_text(json.dumps(
        {"meta": meta, "zips": json.loads(site.to_json(orient="records"))}, indent=1, default=float))

    print(f"sample {len(main_df)} zips, excluded {len(excluded)}")
    print(fit.summary().tables[1], f"\nR2 = {fit.rsquared:.3f}, residual SD = {sd:.1f}")
    print("MAIN:", result)
    print("IL ONLY:", robustness["illinois_only"])
    print("FIRST RUN:", {k: v for k, v in first.items() if k not in ("std_errors", "p_values")})
    print("DROP ONE:", {k: v["value_picks"] for k, v in robustness["drop_one"].items()})
    show = ["zcta", "place_name", "county", "sales_12m", "ppsf", "predicted", "residual_sd", "quality",
            "p_schools", "p_safety", "p_commute", "p_walkability", "tax_rate", "on_list", "dropone_runs_as_pick", "il_only_pick"]
    print("\nVALUE PICKS:\n", main_df[main_df.value_pick].sort_values("residual")[show].round(2).to_string(index=False))
    print("\nMOST UNDERPRICED 10:\n", scores.head(10)[show].round(2).to_string(index=False))
    print("\nMOST OVERPRICED 10:\n", scores.tail(10)[show].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
