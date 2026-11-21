import numpy as np

from transit.analysis.stats import bootstrap_pct_diff


def test_bootstrap_detects_clear_difference():
    rng = np.random.default_rng(1)
    a, b = rng.normal(90, 5, 40), rng.normal(100, 5, 60)
    r = bootstrap_pct_diff(a, b, n_boot=2000)
    assert -13 < r["pct_diff"] < -7
    assert r["ci_low"] < r["pct_diff"] < r["ci_high"] < 0
    assert r["p_value"] < 0.001


def test_bootstrap_no_difference():
    rng = np.random.default_rng(2)
    r = bootstrap_pct_diff(rng.normal(100, 5, 50), rng.normal(100, 5, 50), n_boot=2000)
    assert r["ci_low"] < 0 < r["ci_high"]
