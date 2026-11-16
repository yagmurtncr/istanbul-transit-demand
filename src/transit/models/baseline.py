"""Walk-forward validation, metrics and simple baselines."""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd


def walk_forward(ts: pd.Series, n_folds: int = 4, test_days: int = 14, gap_hours: int = 0
                 ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Expanding-window splits: train on everything before each test block, never after it."""
    ts = pd.to_datetime(pd.Series(ts)).reset_index(drop=True)
    end = ts.max()
    for k in range(n_folds, 0, -1):
        test_end = end - pd.Timedelta(days=test_days * (k - 1))
        test_start = test_end - pd.Timedelta(days=test_days) + pd.Timedelta(hours=1)
        train_end = test_start - pd.Timedelta(hours=1 + gap_hours)
        train_idx = np.flatnonzero(ts <= train_end)
        test_idx = np.flatnonzero((ts >= test_start) & (ts <= test_end))
        if len(train_idx) and len(test_idx):
            yield train_idx, test_idx


def metrics(y_true, y_pred) -> dict[str, float]:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    err = np.abs(y_true - y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    smape = np.mean(np.divide(2 * err, denom, out=np.zeros_like(err), where=denom > 0)) * 100
    return {"MAE": float(err.mean()), "sMAPE": float(smape),
            "WAPE": float(err.sum() / max(np.abs(y_true).sum(), 1e-9) * 100)}


def seasonal_naive(df: pd.DataFrame, lag: int = 168) -> pd.Series:
    """Predict the value from the same hour `lag` hours earlier (default: same hour last week)."""
    return df[f"lag_{lag}"]
