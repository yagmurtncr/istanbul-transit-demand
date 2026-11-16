import numpy as np
import pandas as pd

from transit.models.baseline import metrics, walk_forward


def test_walk_forward_never_trains_on_future():
    ts = pd.Series(pd.date_range("2024-01-01", periods=24 * 90, freq="h"))
    folds = list(walk_forward(ts, n_folds=4, test_days=14))
    assert len(folds) == 4
    for tr, te in folds:
        assert ts[tr].max() < ts[te].min()


def test_metrics_perfect_and_zero_safe():
    m = metrics([0, 10, 20], [0, 10, 20])
    assert m == {"MAE": 0.0, "sMAPE": 0.0, "WAPE": 0.0}
    assert np.isfinite(metrics([0, 0], [1, 0])["sMAPE"])
