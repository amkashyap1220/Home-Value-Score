"""The housing value model's building blocks (src/value_gap.py), on synthetic data."""
import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from value_gap import IN_LINE, classify, kmeans_folds, loo, morans_i


def synthetic(n=60, seed=1):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n),
                       "lon": rng.uniform(-88.5, -87.5, n), "lat": rng.uniform(41.4, 42.4, n)})
    df["y"] = 1 + 0.5 * df.a - 0.3 * df.b + rng.normal(scale=0.2, size=n)
    return df


def test_loo_matches_refitting_without_each_row():
    df = synthetic()
    pred = loo(df, "y", ["a", "b"])
    for i in [0, 17, 42]:
        rest = df.drop(index=i)
        m = sm.OLS(rest.y, sm.add_constant(rest[["a", "b"]])).fit()
        manual = m.params.const + m.params.a * df.a[i] + m.params.b * df.b[i]
        assert pred[i] == pytest.approx(manual)


def test_loo_uses_a_smaller_model_for_rows_missing_a_term():
    df = synthetic()
    df.loc[5, "b"] = np.nan
    pred = loo(df, "y", ["a", "b"])
    rest = df.drop(index=5)
    m = sm.OLS(rest.y, sm.add_constant(rest[["a"]])).fit()
    assert pred[5] == pytest.approx(m.params.const + m.params.a * df.a[5])
    assert pred.notna().all()


def test_classify_uses_the_in_line_band():
    g = pd.Series([-0.3, -IN_LINE, -0.05, 0, 0.099, IN_LINE, np.nan])
    assert classify(g).tolist()[:6] == ["below", "below", "in_line", "in_line", "in_line", "above"]
    assert pd.isna(classify(g)[6])


def test_morans_i_finds_a_spatial_pattern_and_not_noise():
    df = synthetic(n=200, seed=3)
    smooth = pd.Series(np.sin(df.lon * 6) + np.cos(df.lat * 6))
    noise = pd.Series(np.random.default_rng(4).normal(size=200))
    assert morans_i(df, smooth, perms=199)["p_value"] < 0.01
    assert abs(morans_i(df, noise, perms=199)["moran_i"]) < 0.15


def test_spatial_folds_are_deterministic_and_compact():
    df = synthetic(n=200)
    a, b = kmeans_folds(df), kmeans_folds(df)
    assert (a == b).all() and len(np.unique(a)) == 10
    # zips in the same fold are closer to each other than to the average zip
    pts = np.c_[df.lon, df.lat]
    within = np.mean([np.linalg.norm(pts[a == k] - pts[a == k].mean(0), axis=1).mean() for k in range(10)])
    overall = np.linalg.norm(pts - pts.mean(0), axis=1).mean()
    assert within < overall / 2
