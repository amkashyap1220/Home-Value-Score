"""The fit score (src/value.py): percentiles, closeness, direction, missing data and the top list."""
import numpy as np
import pandas as pd
import pytest

from value import COLUMNS, DIRECTION, MIN_COVERAGE, NAMES, pct, score, top


def frame(n=10, **overrides):
    """n zips whose seven buyer factors run 0..n-1 (so percentiles are easy to read)."""
    df = pd.DataFrame({c: np.arange(n, dtype=float) for c in COLUMNS["buy"]})
    df["zcta"] = [f"6{i:04d}" for i in range(n)]
    for col, values in overrides.items():
        df[col] = values
    return df


def only(name, n=7):
    """Weights that count one factor."""
    return [1 if x == name else 0 for x in NAMES]


def test_pct_counts_ties_as_half():
    v = pd.Series([1, 2, 2, 3])
    assert pct(v, 2) == pytest.approx(50)       # 1 below, 2 equal -> (1 + 1) / 4
    assert pct(v, 0) == 0 and pct(v, 10) == 100
    assert pct(pd.Series([1, np.nan, 3]), 2) == pytest.approx(50)   # missing values are ignored


def test_closeness_is_100_on_target_and_falls_with_distance():
    df = frame()
    close, s, cov = score(df, "buy", [0, 0, 4, 0, 0, 0, 0], only("commute"))
    assert close.commute[4] == pytest.approx(100)
    assert close.commute[2] == pytest.approx(80)    # two zips (20 percentile points) away
    assert close.commute[6] == pytest.approx(80)    # commute is two-sided
    assert s[4] == pytest.approx(100)


@pytest.mark.parametrize("name", ["schools", "safety", "price", "train"])
def test_one_sided_factors_count_beating_the_target_as_on_target(name):
    i = NAMES.index(name)
    targets = [5] * 7
    close, _, _ = score(frame(), "buy", targets, only(name))
    better = 8 if DIRECTION[i] > 0 else 2      # more schools, less crime, lower price, closer station
    worse = 2 if DIRECTION[i] > 0 else 8
    assert close[name][better] == pytest.approx(100)
    assert close[name][worse] < 100


def test_direction_matches_what_better_means():
    assert dict(zip(NAMES, DIRECTION)) == {"schools": 1, "safety": -1, "commute": 0, "walkability": 0,
                                           "home_age": 0, "price": -1, "train": -1}


def test_missing_value_is_left_out_not_scored_as_average():
    crime = np.arange(10, dtype=float)
    crime[3] = np.nan
    df = frame(crimes_per_1000_local=crime)
    weights = [1, 3, 0, 0, 0, 0, 0]               # schools Normal, safety Top
    close, s, cov = score(df, "buy", [9, 0, 0, 0, 0, 0, 0], weights)
    assert np.isnan(close.safety[3])
    assert cov[3] == pytest.approx(0.25)           # only schools' weight is measured
    assert s[3] == pytest.approx(close.schools[3])  # the score is the measured factors' average
    assert cov.drop(3).eq(1).all()


def test_top_list_skips_zips_with_too_little_coverage():
    scores = pd.Series([99, 90, 80, 70], index=[0, 1, 2, 3], dtype=float)
    coverage = pd.Series([0.5, 1, MIN_COVERAGE, 0.79])
    assert top(scores, coverage, n=3).index.tolist() == [1, 2]


def test_zero_weight_factors_do_not_affect_score_or_coverage():
    df = frame(walk_index=[np.nan] * 10)
    weights = [1, 0, 0, 0, 0, 0, 0]
    _, s, cov = score(df, "buy", [9, 0, 0, 0, 0, 0, 0], weights)
    assert cov.eq(1).all()
    assert s.notna().all()
