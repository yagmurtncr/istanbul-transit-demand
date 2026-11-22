"""Feature engineering. Every lag/rolling feature uses only data available at forecast time."""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = (24, 48, 168)          # same hour yesterday, two days ago, last week
ROLL_WINDOWS = (24, 168)


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ts = out["timestamp"]
    out["hour"] = ts.dt.hour
    out["dow"] = ts.dt.day_of_week
    out["month"] = ts.dt.month
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["date"] = ts.dt.normalize()
    return out


def add_lags(df: pd.DataFrame, target: str = "passengers", group: str = "transport_type") -> pd.DataFrame:
    out = df.sort_values([group, "timestamp"]).copy()
    g = out.groupby(group)[target]
    for lag in LAGS:
        out[f"lag_{lag}"] = g.shift(lag)
    # Rolling stats end 24h before the target hour, so a day-ahead forecast never sees the future.
    shifted = g.shift(24)
    for w in ROLL_WINDOWS:
        out[f"roll_mean_{w}"] = (shifted.groupby(out[group])
                                 .transform(lambda s, w=w: s.rolling(w, min_periods=w // 2).mean()))
    return out


def build_features(hourly: pd.DataFrame, weather: pd.DataFrame | None, cal: pd.DataFrame | None,
                   group: str = "transport_type") -> pd.DataFrame:
    df = add_calendar(hourly)
    if weather is not None:
        df = df.merge(weather, on="timestamp", how="left")
    if cal is not None:
        df = df.merge(cal, on="date", how="left")
    return add_lags(df, group=group)
