"""Effect estimates with bootstrap confidence intervals and non-parametric tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def bootstrap_pct_diff(treated, control, n_boot: int = 5000, seed: int = 0) -> dict:
    """% difference of means (treated vs control) with a percentile bootstrap 95% CI and Mann-Whitney p-value."""
    a, b = np.asarray(treated, float), np.asarray(control, float)
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        boots[i] = rng.choice(a, a.size).mean() / rng.choice(b, b.size).mean() - 1
    p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue if a.size and b.size else np.nan
    return {"n_treated": int(a.size), "n_control": int(b.size),
            "pct_diff": float((a.mean() / b.mean() - 1) * 100),
            "ci_low": float(np.percentile(boots, 2.5) * 100), "ci_high": float(np.percentile(boots, 97.5) * 100),
            "p_value": float(p)}


def daily_table(hourly: pd.DataFrame, weather: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    """One row per day and mode: passengers, daily rain (mm), mean temperature, calendar flags."""
    d = hourly.assign(date=hourly["timestamp"].dt.normalize())
    daily = d.groupby(["date", "transport_type"], as_index=False)["passengers"].sum()
    w = weather.assign(date=weather["timestamp"].dt.normalize())
    # Rain that matters for commuting: 06:00-22:00
    w = w[w["timestamp"].dt.hour.between(6, 21)]
    wd = w.groupby("date", as_index=False).agg(rain_mm=("precipitation", "sum"), temp=("temperature_2m", "mean"))
    out = daily.merge(wd, on="date", how="left").merge(cal, on="date", how="left")
    out["dow"] = out["date"].dt.dayofweek
    return out


def rain_effect(daily: pd.DataFrame, mode: str, threshold_mm: float = 2.0) -> dict:
    """Rainy vs dry working days (Mon-Fri, no holiday/eve), same weekday mix."""
    x = daily[(daily["transport_type"] == mode) & (daily["dow"] < 5) & (daily["is_holiday"] == 0) & (daily["is_eve"] == 0)]
    rainy, dry = x[x["rain_mm"] >= threshold_mm], x[x["rain_mm"] < 0.2]
    return bootstrap_pct_diff(rainy["passengers"], dry["passengers"])


def holiday_effect(daily: pd.DataFrame, mode: str) -> dict:
    """Public-holiday weekdays vs ordinary weekdays."""
    x = daily[(daily["transport_type"] == mode) & (daily["dow"] < 5)]
    hol = x[x["is_holiday"] == 1]
    normal = x[(x["is_holiday"] == 0) & (x["is_eve"] == 0)]
    return bootstrap_pct_diff(hol["passengers"], normal["passengers"])
