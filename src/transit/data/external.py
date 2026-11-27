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


WEATHER_CSV = Path(__file__).resolve().parents[3] / "data" / "aggregated" / "weather_istanbul_2022-01_2024-07.csv"


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
        "is_religious_holiday": [int(is_religious(d)) for d in days],
        "is_national_holiday": [int(d in tr and not is_arife(d) and not is_religious(d)) for d in days],
        # half working days: religious eves (arife) and 28 Ekim, the eve of Republic Day
        "is_half_day": [int(d in eves or (d.month == 10 and d.day == 28)) for d in days],
        "is_ramadan": [int(any(pd.Timestamp(a) <= pd.Timestamp(d) <= pd.Timestamp(b) for a, b in RAMADAN))
                       for d in days],
        "is_bridge": [int(d.isoformat() in BRIDGE_DAYS) for d in days],
        "is_election": [int(d.isoformat() in ELECTION_DAYS) for d in days],
    })


# Primary/secondary school breaks, weekends included (MEB çalışma takvimleri 2021-22 ... 2026-27).
# 2024-25 onwards is only used by the "future day" forecast in the app.
SCHOOL_BREAKS = [
    ("2022-01-22", "2022-02-06"),   # semester break 2021-22
    ("2022-04-09", "2022-04-17"),   # 2nd mid-term break
    ("2022-06-18", "2022-09-11"),   # summer 2022
    ("2022-11-12", "2022-11-20"),   # 1st mid-term break 2022-23
    ("2023-01-21", "2023-02-19"),   # semester break, extended nationwide after the 6 Feb 2023 earthquakes
    ("2023-04-15", "2023-04-23"),   # 2nd mid-term break + Ramazan Bayramı
    ("2023-06-17", "2023-09-10"),   # summer 2023
    ("2023-11-11", "2023-11-19"),   # 1st mid-term break 2023-24
    ("2024-01-20", "2024-02-04"),   # semester break
    ("2024-04-06", "2024-04-14"),   # 2nd mid-term break (with Ramazan Bayramı)
    ("2024-06-15", "2024-09-08"),   # summer 2024
    ("2024-11-09", "2024-11-17"),   # 1st mid-term break 2024-25
    ("2025-01-18", "2025-02-02"),   # semester break
    ("2025-03-29", "2025-04-06"),   # 2nd mid-term break (with Ramazan Bayramı)
    ("2025-06-21", "2025-09-07"),   # summer 2025
    ("2025-11-08", "2025-11-16"),   # 1st mid-term break 2025-26
    ("2026-01-17", "2026-02-01"),   # semester break
    ("2026-03-14", "2026-03-22"),   # 2nd mid-term break (with Ramazan Bayramı)
    ("2026-06-27", "2026-09-13"),   # summer 2026
    ("2026-11-14", "2026-11-22"),   # 1st mid-term break 2026-27
    ("2027-01-23", "2027-02-07"),   # semester break
    ("2027-03-06", "2027-03-14"),   # 2nd mid-term break (with Ramazan Bayramı)
    ("2027-06-26", "2027-09-12"),   # summer 2027 (end date approximate)
]

# Administrative leave for public employees that turned a bayram into a 9-day holiday ("köprü" days).
BRIDGE_DAYS = ["2022-07-13", "2022-07-14", "2023-06-26", "2023-06-27", "2024-04-08", "2024-04-09",
               "2024-06-20", "2024-06-21"]
# Ramazan (fasting month, Diyanet): evening demand shifts around iftar.
RAMADAN = [("2022-04-02", "2022-05-01"), ("2023-03-23", "2023-04-20"), ("2024-03-11", "2024-04-09"),
           ("2025-03-01", "2025-03-29"), ("2026-02-19", "2026-03-19"), ("2027-02-08", "2027-03-08")]
# National elections (presidential / parliamentary / local).
ELECTION_DAYS = ["2023-05-14", "2023-05-28", "2024-03-31"]


def _school_closed(day: pd.Timestamp) -> bool:
    return any(pd.Timestamp(a) <= day <= pd.Timestamp(b) for a, b in SCHOOL_BREAKS)
