"""Housing value: is a zip's price per square foot lower or higher than the zips' measured
characteristics would lead us to expect? (added 2026-10-22; method in docs/decisions.md,
results in docs/results.md)

This is separate from the map's fit score (src/value.py). The fit score says how well a zip
matches what one reader wants. This model says nothing about the reader: it compares each
zip's price with the price of zips that look like it on paper. A zip can be a great fit and
expensive for what it is, or a poor fit and cheap for what it is.

Model (ordinary least squares on the buyers' sample):

  log(price per sq ft) = b0 + b1 schools + b2 log(1 + crimes per 1,000) + b3 commute minutes
                       + b4 walk index + b5 log(miles to a train station + 0.25) + b6 home age
                       + b7 Indiana + b8 Chicago + error

- The log makes coefficients percentage effects and tames the long right tail of prices.
- Each indicator enters on its own, so the data sets their weights, instead of the
  pre-registered equal-weight quality score.
- Controls for the mix of homes (single-family share and median rooms, src/structure.py) were
  tried and are kept as a sensitivity check only: they did not improve out-of-sample error.
- Indiana: different taxes (the 1% homestead cap) and different school tests. Chicago: one
  school district, so its school value is the same for every city zip and its level has to be
  estimated separately.

Value gap = actual / expected - 1, where "expected" is the zip's leave-one-out prediction (the
model fitted without that zip), so a zip's own price never pulls its expectation towards itself.
A zip missing an indicator (mostly crime) is predicted by the same model fitted without that
indicator, and flagged.

Checks, all reported in output/value_gap.json and docs/results.md:
  validation   out-of-sample error of this model against simple baselines (metro average,
               county average, the pre-registered model, the previous main model), with
               random 10-fold and spatial 10-fold cross-validation (folds are clusters of
               nearby zips, so a zip is never predicted from its neighbours)
  spatial      Moran's I of the residuals (8 nearest neighbours)
  sensitivity  the gap under 12 other specifications; agreement = share with the same sign
  persistence  the same model on the 2024 and 2025 price windows
  noise        sampling error of a zip's median price per sq ft, from how much it moves
               between two years: var(change) ~ b x (1/n1 + 1/n2), so SE ~ sqrt(b / sales)

Outputs: output/value_gap.csv (one row per zip), output/value_gap.json (model, checks)
"""
import json

import numpy as np
import pandas as pd
import shapely
import statsmodels.api as sm

from fetch import ROOT
from model import INDICATORS, LABELS
from value import load

P, OUT = ROOT / "data/processed", ROOT / "output"
INDICATOR_TERMS = ["school_pct", "log_crime", "commute_min", "walk_index", "log_station", "home_age"]
STOCK_TERMS = ["sf_detached_share", "median_rooms"]
REGION_TERMS = ["indiana", "chicago"]
TERMS = INDICATOR_TERMS + REGION_TERMS
TERM_LABELS = {"school_pct": "Schools (percentile)", "log_crime": "log(1 + crimes per 1,000)", "commute_min": "Commute (minutes)",
               "walk_index": "Walk index", "log_station": "log(miles to station + 0.25)", "home_age": "Home age (years)",
               "sf_detached_share": "Single-family share", "median_rooms": "Median rooms", "indiana": "Indiana",
               "chicago": "Chicago", "tax_rate": "Tax rate"}
SHORT = {"school_pct": "schools", "log_crime": "safety", "commute_min": "commute", "walk_index": "walkability",
         "log_station": "train station", "home_age": "home age"}
IN_LINE = 0.10          # gaps within +-10% count as "in line with expected"
FEW_SALES = 50          # fewer sales than this is flagged as a noisy price
AGREE = 0.8             # a gap is "robust" when at least 80% of the other specifications agree on its sign
K_FOLDS, SEED = 10, 2026


def build():
    """The buyers' sample from src/value.py with the model's columns."""
    r = lambda n: pd.read_csv(P / n, dtype={"zcta": str})
    df = load()["buy"]
    df = df[df.ppsf.notna()].copy()
    df = (df.merge(r("structure.csv")[["zcta", *STOCK_TERMS]], on="zcta", how="left")
          .merge(r("extras.csv")[["zcta", "home_energy_month", "commute_fuel_year"]], on="zcta", how="left"))
    hist = r("price_history.csv")
    for ptype, year, col in [("all", "2025-05-31", "ppsf_2025"), ("all", "2024-05-31", "ppsf_2024"),
                             ("all", "2023-05-31", "ppsf_2023"), ("single_family", "2026-05-31", "ppsf_sf")]:
        h = hist[(hist.property_type == ptype) & (hist.window_end == year)].set_index("zcta")
        df[col] = df.zcta.map(h.ppsf.where(h.sales >= 20))
    shapes = json.loads((OUT / "site/chicago-home-value-zips.json").read_text())
    center = {f["id"]: shapely.from_geojson(json.dumps(f["geometry"])).centroid for f in shapes["features"]}
    df["lon"] = df.zcta.map(lambda z: center[z].x)
    df["lat"] = df.zcta.map(lambda z: center[z].y)
    df["log_ppsf"] = np.log(df.ppsf)
    df["log_crime"] = np.log1p(df.crimes_per_1000_local)
    df["log_crime_agency"] = np.log1p(df.crimes_per_1000)
    df["log_station"] = np.log(df.station_mi + 0.25)
    df["indiana"] = (df.state == "IN").astype(float)
    df["chicago"] = (df.place_name == "Chicago").astype(float)
    # The pre-registered quality score (equal-weight percentiles), for the baseline models
    for col, higher in INDICATORS.items():
        rk = df[col].rank(ascending=higher, method="average")
        df[f"p_{LABELS[col]}"] = (rk - 1) / (rk.count() - 1) * 100
    df["quality"] = df[[f"p_{v}" for v in LABELS.values()]].mean(axis=1)
    return df.reset_index(drop=True)


def classify(gap):
    return pd.Series(np.select([gap <= -IN_LINE, gap >= IN_LINE], ["below", "above"], "in_line"), index=gap.index).where(gap.notna())


def design(df, terms):
    X = df[terms].astype(float)
    return sm.add_constant(X, has_constant="add")


def loo(df, y, terms):
    """Leave-one-out predictions of y. Each zip uses only the terms it has: zips with the
    same missing pattern share a model fitted on every zip complete for those terms."""
    pred = pd.Series(np.nan, index=df.index)
    have = df[terms].notna()
    for pattern, rows in have.groupby(list(terms)).groups.items():
        pattern = (pattern,) if not isinstance(pattern, tuple) else pattern
        use = [t for t, h in zip(terms, pattern) if h]
        fit_rows = df.index[df[use].notna().all(axis=1) & df[y].notna()]
        sub = df.loc[fit_rows]
        X = design(sub, use)
        X = X.loc[:, X.std() > 0].assign(const=1.0)
        m = sm.OLS(sub[y], X).fit()
        press = m.get_influence().resid_press
        loo_pred = pd.Series(sub[y].values - press, index=fit_rows)
        inside = [i for i in rows if i in loo_pred.index]
        pred[inside] = loo_pred[inside]
        outside = [i for i in rows if i not in loo_pred.index]   # rows without y: an ordinary prediction
        if outside:
            pred[outside] = m.predict(design(df.loc[outside], use)[X.columns])
    return pred


def kmeans_folds(df, k=K_FOLDS, seed=SEED, iters=100):
    """Spatial folds: k-means clusters of zip centers (in miles), so test zips are surrounded by other test zips."""
    pts = np.c_[df.lon * 69 * np.cos(np.radians(41.8)), df.lat * 69]
    rng = np.random.default_rng(seed)
    centers = pts[rng.choice(len(pts), k, replace=False)]
    for _ in range(iters):
        lab = np.argmin(((pts[:, None] - centers[None]) ** 2).sum(-1), axis=1)
        new = np.array([pts[lab == j].mean(0) if (lab == j).any() else centers[j] for j in range(k)])
        if np.allclose(new, centers):
            break
        centers = new
    return lab


def random_folds(df, k=K_FOLDS, seed=SEED):
    return np.random.default_rng(seed).permutation(np.arange(len(df)) % k)


# ---- Models compared in cross-validation. Each returns predictions of log(price per sq ft) for the test rows.

def ols_log(terms):
    def f(train, test):
        tr = train.dropna(subset=terms)
        X = design(tr, terms)
        X = X.loc[:, X.std() > 0].assign(const=1.0)
        m = sm.OLS(tr.log_ppsf, X).fit()
        out = pd.Series(np.nan, index=test.index)
        te = test.dropna(subset=terms)
        out[te.index] = m.predict(design(te, terms)[X.columns])
        # Zips missing a term (mostly crime) use the model without it, as in loo()
        rest = test.index[out.isna()]
        if len(rest):
            avail = [t for t in terms if test.loc[rest, t].notna().all()]
            out[rest] = ols_log(avail)(train, test.loc[rest])
        return out
    return f


def ols_level(terms):
    """The earlier models were fitted to price per sq ft in dollars; their predictions are logged to compare."""
    def f(train, test):
        tr = train.dropna(subset=terms)
        m = sm.OLS(tr.ppsf, design(tr, terms)).fit()
        te = test[terms].fillna(train[terms].mean())
        return np.log(np.maximum(m.predict(design(te, terms)), 20))
    return f


def metro_mean(train, test):
    return pd.Series(train.log_ppsf.mean(), index=test.index)


def county_mean(train, test):
    means = train.groupby("county").log_ppsf.mean()
    return test.county.map(means).fillna(train.log_ppsf.mean())


MODELS = {
    "Metro average": metro_mean,
    "County average": county_mean,
    "Pre-registered: $/sq ft ~ quality score + tax rate": ols_level(["quality", "tax_rate"]),
    "Previous main: + home age, energy bills, commuting fuel": ols_level(["quality", "tax_rate", "home_age", "home_energy_month", "commute_fuel_year"]),
    "This model: log $/sq ft ~ six indicators + Indiana + Chicago": ols_log(TERMS),
    "This model + single-family share and rooms": ols_log(TERMS + STOCK_TERMS),
}


def cross_validate(df, folds):
    out = {}
    for name, f in MODELS.items():
        pred = pd.Series(np.nan, index=df.index)
        for k in np.unique(folds):
            test = df[folds == k]
            pred[test.index] = f(df[folds != k], test)
        err = df.log_ppsf - pred
        out[name] = {
            "rmse_log": float(np.sqrt((err ** 2).mean())),
            "median_abs_pct_error": float((np.exp(err.abs()) - 1).median() * 100),
            "r2_log": float(1 - (err ** 2).sum() / ((df.log_ppsf - df.log_ppsf.mean()) ** 2).sum()),
        }
    return out


def morans_i(df, resid, k=8, perms=999, seed=SEED):
    """Moran's I of the residuals with row-standardized k-nearest-neighbour weights, and a permutation p-value."""
    ok = resid.notna().values
    pts = np.c_[df.lon * np.cos(np.radians(41.8)), df.lat][ok]
    z = (resid[ok] - resid[ok].mean()).values
    d = ((pts[:, None] - pts[None]) ** 2).sum(-1)
    np.fill_diagonal(d, np.inf)
    nn = np.argsort(d, axis=1)[:, :k]
    stat = lambda v: (v * v[nn].mean(1)).sum() / (v ** 2).sum()
    obs = stat(z)
    rng = np.random.default_rng(seed)
    null = np.array([stat(rng.permutation(z)) for _ in range(perms)])
    return {"moran_i": float(obs), "p_value": float(((null >= obs).sum() + 1) / (perms + 1)), "k": k}


def sales_noise(df):
    """b in var(change in log $/sq ft between two windows) ~ b x (1/n1 + 1/n2), pooled over three year pairs."""
    hist = pd.read_csv(P / "price_history.csv", dtype={"zcta": str})
    a = hist[hist.property_type == "all"].pivot(index="zcta", columns="window_end", values=["ppsf", "sales"])
    xs, ys = [], []
    for y1, y2 in [("2023-05-31", "2024-05-31"), ("2024-05-31", "2025-05-31"), ("2025-05-31", "2026-05-31")]:
        d = np.log(a["ppsf"][y2]) - np.log(a["ppsf"][y1])
        d = d - d.median()
        ok = (a["sales"][y1] >= 20) & (a["sales"][y2] >= 20) & d.notna()
        xs.append((1 / a["sales"][y1] + 1 / a["sales"][y2])[ok])
        ys.append(d[ok] ** 2)
    x, y = pd.concat(xs), pd.concat(ys)
    return float((x * y).sum() / (x * x).sum())   # least squares through the origin


def coefficients(df):
    cc = df.dropna(subset=TERMS)
    X = design(cc, TERMS)
    robust = sm.OLS(cc.log_ppsf, X).fit(cov_type="HC1")
    clustered = sm.OLS(cc.log_ppsf, X).fit(cov_type="cluster", cov_kwds={"groups": cc.county.astype("category").cat.codes})
    rows = [{"term": t, "label": TERM_LABELS.get(t, "Intercept"), "coef": float(robust.params[t]),
             "pct_effect": float((np.exp(robust.params[t]) - 1) * 100), "se_hc1": float(robust.bse[t]),
             "p_hc1": float(robust.pvalues[t]), "se_county": float(clustered.bse[t]), "p_county": float(clustered.pvalues[t])}
            for t in X.columns]
    return rows, robust, len(cc)


def main():
    df = build()
    n = len(df)

    # The value gap from the main model, leave-one-out
    df["expected_log"] = loo(df, "log_ppsf", TERMS)
    df["gap_log"] = df.log_ppsf - df.expected_log
    df["expected_ppsf"] = np.exp(df.expected_log)
    df["gap"] = np.exp(df.gap_log) - 1
    sd = float(df.gap_log.std())

    # Sampling noise of the zip's price, and a 90% interval for the gap from that noise alone
    b = sales_noise(df)
    df["price_se"] = np.sqrt(b / df.sales_12m)
    df["gap_lo"] = np.exp(df.gap_log - 1.645 * df.price_se) - 1
    df["gap_hi"] = np.exp(df.gap_log + 1.645 * df.price_se) - 1

    # Sensitivity: the same gap under other specifications
    df["log_ppsf_sf"] = np.log(df.ppsf_sf)
    counties = pd.get_dummies(df.county, prefix="c", drop_first=True, dtype=float)
    cdf = pd.concat([df, counties], axis=1)
    variants = {
        "no Indiana or Chicago terms": (df, "log_ppsf", INDICATOR_TERMS + STOCK_TERMS),
        "adding the tax rate": (df, "log_ppsf", TERMS + ["tax_rate"]),
        "adding the housing stock": (df, "log_ppsf", TERMS + STOCK_TERMS),
        "agency crime rates (one rate for Chicago)": (df, "log_ppsf", [t if t != "log_crime" else "log_crime_agency" for t in TERMS]),
        "single-family homes only": (df, "log_ppsf_sf", TERMS),
        "county fixed effects": (cdf, "log_ppsf", TERMS + list(counties.columns)),
        **{"without " + SHORT[t]: (df, "log_ppsf", [x for x in TERMS if x != t]) for t in INDICATOR_TERMS},
    }
    gaps = pd.DataFrame({name: np.exp(d[y] - loo(d, y, terms)) - 1 for name, (d, y, terms) in variants.items()})
    df["value_class"] = classify(df.gap)
    same = gaps.apply(classify).eq(df.value_class, axis=0).where(gaps.notna())
    df["agreement"] = same.mean(axis=1)
    df["variants"] = gaps.notna().sum(axis=1)

    # Persistence: the same model on earlier price windows
    for year in ["2025", "2024", "2023"]:
        d = df.assign(y=np.log(df[f"ppsf_{year}"]))
        df[f"gap_{year}"] = np.exp(d.y - loo(d, "y", TERMS)) - 1

    # Confidence: how many reasons there are to doubt the zip's class
    issues = pd.DataFrame({
        "few_sales": df.sales_12m < FEW_SALES,
        "missing_indicator": df[["school_pct", "crimes_per_1000_local", "commute_min", "walk_index"]].isna().any(axis=1),
        "chicago_schools": df.chicago == 1,
        "spec_sensitive": df.agreement < AGREE,
        "changed_since_2025": df.gap_2025.notna() & classify(df.gap_2025).ne(df.value_class),
        # price noise alone could put a below/above zip back in line
        "noisy_price": ((df.value_class == "below") & (df.gap_hi > -IN_LINE)) | ((df.value_class == "above") & (df.gap_lo < IN_LINE)),
    })
    df["issues"] = issues.apply(lambda r: [k for k, v in r.items() if v], axis=1)
    count = issues.sum(axis=1)
    df["confidence"] = np.select([count == 0, count == 1], ["high", "medium"], "low")

    # Validation
    spatial = kmeans_folds(df)
    validation = {"random_10_fold": cross_validate(df, random_folds(df)), "spatial_10_fold": cross_validate(df, spatial)}
    coefs, fit, n_complete = coefficients(df)
    in_sample_pre = sm.OLS(df.ppsf, design(df, ["quality", "tax_rate"])).fit()
    spatial_check = {
        "this_model_loo_residuals": morans_i(df, df.gap_log),
        "pre_registered_residuals": morans_i(df, np.log(df.ppsf) - np.log(in_sample_pre.fittedvalues.clip(lower=20))),
    }
    persistence = {year: {"n": int(df[f"gap_{year}"].notna().sum()),
                          "correlation": float(np.log1p(df.gap).corr(np.log1p(df[f"gap_{year}"]))),
                          "same_sign": float((np.sign(df.gap) == np.sign(df[f"gap_{year}"]))[df[f"gap_{year}"].notna()].mean())}
                   for year in ["2025", "2024", "2023"]}
    # Exploratory, not used anywhere: did zips below expected in 2023 rise faster to 2026?
    later = np.log(df.ppsf) - np.log(df.ppsf_2023)
    catch_up = {"n": int(later.notna().sum()), "correlation_gap2023_vs_growth": float(np.log1p(df.gap_2023).corr(later))}

    summary = {
        "n": n, "n_complete": n_complete, "r2_in_sample": float(fit.rsquared), "adj_r2_in_sample": float(fit.rsquared_adj),
        "loo_residual_sd_log": sd, "in_line_band": IN_LINE, "few_sales": FEW_SALES, "agreement_threshold": AGREE,
        "sales_noise_b": b, "price_window": "2025-06-01 to 2026-05-31",
        "coefficients": coefs, "validation": validation, "spatial_autocorrelation": spatial_check,
        "persistence": persistence, "catch_up_exploratory": catch_up,
        "variants": list(variants),
        "variant_correlation_with_main": {k: float(np.log1p(df.gap).corr(np.log1p(gaps[k]))) for k in gaps},
        "variant_same_class": {k: float(same[k].mean()) for k in gaps},
        "classes": df.value_class.value_counts().to_dict(),
        "confidence": df.confidence.value_counts().to_dict(),
        "class_by_confidence": pd.crosstab(df.value_class, df.confidence).to_dict(),
        "issue_counts": issues.sum().astype(int).to_dict(),
    }
    (OUT / "value_gap.json").write_text(json.dumps(summary, indent=2))
    cols = ["zcta", "place_name", "state", "county", "sales_12m", "ppsf", "expected_ppsf", "gap", "gap_lo", "gap_hi",
            "price_se", "value_class", "confidence", "agreement", "variants", "gap_2025", "gap_2024", "gap_2023", "ppsf_sf"]
    out = df[cols].assign(issues=df.issues.map(";".join)).sort_values("gap")
    out.to_csv(OUT / "value_gap.csv", index=False, float_format="%.4g")

    print(f"n = {n} ({n_complete} complete), in-sample R2 = {fit.rsquared:.3f}, LOO residual SD = {sd:.3f} (log)")
    print(pd.DataFrame(coefs).set_index("term")[["coef", "pct_effect", "se_hc1", "p_hc1", "se_county", "p_county"]].round(4).to_string())
    for kind, v in validation.items():
        print(f"\n{kind}\n" + pd.DataFrame(v).T.round(3).to_string())
    print("\nMoran's I:", spatial_check)
    print("persistence:", persistence)
    print("catch-up (exploratory):", catch_up)
    print("sales noise b:", round(b, 4), "-> SE at 20 / 50 / 200 sales:", [round(np.sqrt(b / s), 3) for s in (20, 50, 200)])
    print("variant correlations:", {k: round(v, 2) for k, v in summary["variant_correlation_with_main"].items()})
    print("classes:", summary["classes"], "confidence:", summary["confidence"], "issues:", summary["issue_counts"])
    print(pd.crosstab(df.value_class, df.confidence))
    show = ["zcta", "place_name", "state", "sales_12m", "ppsf", "expected_ppsf", "gap", "agreement", "gap_2025", "confidence"]
    print("\nMOST BELOW EXPECTED\n", df.sort_values("gap")[show].head(20).round(2).to_string(index=False))
    print("\nMOST ABOVE EXPECTED\n", df.sort_values("gap")[show].tail(12).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
