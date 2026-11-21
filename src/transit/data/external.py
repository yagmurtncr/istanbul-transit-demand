"""External signals: hourly weather (Open-Meteo) and Turkish public holidays."""
from __future__ import annotations

import time

import holidays
import pandas as pd
import requests

from transit.config import LAT, LON, TIMEZONE

WEATHER_VARS = ["temperature_2m", "precipitation", "snowfall", "wind_speed_10m"]


def fetch_weather(start: str, end: str) -> pd.DataFrame:
    """Historical hourly weather for Istanbul in local time."""
    for attempt in range(4):
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": LAT, "longitude": LON, "start_date": start, "end_date": end,
                    "hourly": ",".join(WEATHER_VARS), "timezone": TIMEZONE},
            timeout=60,
        )
        if r.status_code != 429 or attempt == 3:
            break
        time.sleep(20 * (attempt + 1))  # free API rate limit
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"]).rename(columns={"time": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def holiday_calendar(start: str, end: str) -> pd.DataFrame:
    """One row per day: public-holiday flag, holiday name and religious-holiday eve (arife)."""
    days = pd.date_range(start, end, freq="D")
    tr = holidays.Turkey(years=range(days.min().year, days.max().year + 1))
    df = pd.DataFrame({"date": days})
    df["is_holiday"] = df["date"].dt.date.map(lambda d: d in tr).astype(int)
    df["holiday_name"] = df["date"].dt.date.map(lambda d: tr.get(d, ""))
    religious = df["holiday_name"].str.contains("Bayram", na=False)
    first_days = df.loc[religious & ~religious.shift(1, fill_value=False), "date"]
    df["is_eve"] = df["date"].isin(first_days - pd.Timedelta(days=1)).astype(int)
    return df
