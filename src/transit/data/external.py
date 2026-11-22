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
    """One row per day: public-holiday flag, holiday name, religious-holiday eve (arife), school break."""
    days = pd.date_range(start, end, freq="D")
    tr = holidays.Turkey(years=range(days.min().year, days.max().year + 1))
    # Compare as Timestamps: Series.dt.date returns different types across pandas versions/backends.
    names = {pd.Timestamp(d): str(n) for d, n in tr.items()}
    df = pd.DataFrame({"date": days})
    df["holiday_name"] = df["date"].map(names).fillna("")
    is_arife = df["holiday_name"].str.contains("rife", case=False)       # some versions list the half-day eve
    df["is_holiday"] = ((df["holiday_name"] != "") & ~is_arife).astype(int)
    religious = df["holiday_name"].str.contains("Bayram", na=False) & ~is_arife & df["holiday_name"].str.contains(
        "Ramazan|Kurban", na=False)
    first_days = df.loc[religious & ~religious.shift(1, fill_value=False), "date"]
    df["is_eve"] = (df["date"].isin(first_days - pd.Timedelta(days=1)) | is_arife).astype(int)
    df["school_closed"] = df["date"].map(_school_closed).astype(int)
    return df


# Primary/secondary school breaks (MEB çalışma takvimi). Extend when adding more years.
SCHOOL_BREAKS = [
    ("2023-06-17", "2023-09-10"),   # summer 2023
    ("2023-11-13", "2023-11-17"),   # 1st mid-term break
    ("2024-01-20", "2024-02-04"),   # semester break
    ("2024-04-06", "2024-04-14"),   # 2nd mid-term break (with Ramazan Bayramı)
    ("2024-06-15", "2024-09-08"),   # summer 2024
]


def _school_closed(day: pd.Timestamp) -> bool:
    return any(pd.Timestamp(a) <= day <= pd.Timestamp(b) for a, b in SCHOOL_BREAKS)
