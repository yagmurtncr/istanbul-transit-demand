"""External signals: hourly weather (Open-Meteo) and Turkish public holidays."""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

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


WEATHER_CSV = Path(__file__).resolve().parents[3] / "data" / "aggregated" / "weather_istanbul_2024-01_2024-07.csv"


def load_weather(start: str, end: str) -> pd.DataFrame:
    """Hourly weather: the bundled CSV when it covers the period (offline, e.g. in the browser demo),
    otherwise the Open-Meteo archive API."""
    if WEATHER_CSV.exists():
        df = pd.read_csv(WEATHER_CSV, parse_dates=["timestamp"])
        if df["timestamp"].min() <= pd.Timestamp(start) and df["timestamp"].max() >= pd.Timestamp(end):
            return df
    return fetch_weather(start, end)


def holiday_calendar(start: str, end: str) -> pd.DataFrame:
    """One row per day: public-holiday flag, holiday name, religious-holiday eve (arife), school break.

    Built with plain Python dates on purpose: Series.dt.date / shift / isin behave differently
    across pandas versions and backends, and this table must be identical everywhere.
    """
    days = [d.date() for d in pd.date_range(start, end, freq="D")]
    years = range(days[0].year, days[-1].year + 1)
    try:  # pin the language so holiday names do not depend on the machine's locale
        tr = holidays.Turkey(years=years, language="tr")
    except (TypeError, NotImplementedError):
        tr = holidays.Turkey(years=years)
    one = dt.timedelta(days=1)

    def is_arife(day) -> bool:          # some versions list the half-day eve itself
        name = str(tr.get(day, "")).lower()
        return "arife" in name or " eve" in name

    def is_religious(day) -> bool:
        name = str(tr.get(day, ""))
        keys = ("Ramazan", "Kurban", "Ramadan", "Sacrifice", "Eid")
        return any(k in name for k in keys) and not is_arife(day)

    eves = {d - one for d in tr if is_religious(d) and not is_religious(d - one)}
    eves |= {d for d in tr if is_arife(d)}
    return pd.DataFrame({
        "date": pd.to_datetime(days),
        "is_holiday": [int(d in tr and not is_arife(d)) for d in days],
        "holiday_name": [str(tr.get(d, "")) for d in days],
        "is_eve": [int(d in eves) for d in days],
        "school_closed": [int(_school_closed(pd.Timestamp(d))) for d in days],
    })


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
