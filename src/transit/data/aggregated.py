"""Pre-aggregated İBB data shipped with the repo (data/aggregated/).

The raw monthly CSVs are ~1.6 GB each. They were streamed once and summed to one row per
(date, hour, transport type), which is everything the forecasting models need.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from transit.config import DATA

HOURLY = DATA / "aggregated" / "hourly_by_mode_2024-01_2024-07.csv"
RAIL_LINES = DATA / "aggregated" / "rail_lines_daily_2024-01_2024-07.csv"


def load_hourly(path: Path = HOURLY) -> pd.DataFrame:
    """Columns: timestamp, transport_type (road/rail/sea), passengers. Same shape as clean.to_hourly()."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"], unit="h")
    return df[["timestamp", "transport_type", "passengers"]].sort_values(["transport_type", "timestamp"]).reset_index(drop=True)


def load_rail_lines(path: Path = RAIL_LINES) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    return df
