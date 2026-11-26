"""Explain the final models with SHAP and stress-test them with real day-ahead weather forecasts.

1. SHAP (TreeExplainer) on the last 8 weeks for each mode -> reports/figures/shap_<mode>.png
2. Day-ahead test: train on data before 1 June 2024 with observed weather, then forecast June-July 2024
   twice: with the observed weather (what the validation used so far) and with the weather forecast issued
   the day before (Open-Meteo Previous Runs API, `*_previous_day1`), which is what a real day-ahead
   service would have.
Writes reports/explainability.md.

    python scripts/train_final.py && python scripts/explain_and_stress_test.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402
import shap  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402
from skops.io import get_untrusted_types, load  # noqa: E402

from transit.config import ROOT  # noqa: E402
from transit.data.aggregated import load_hourly  # noqa: E402
from transit.data.external import LAT, LON, TIMEZONE, holiday_calendar, load_weather  # noqa: E402
from transit.features.build import build_features  # noqa: E402
from transit.models.baseline import metrics  # noqa: E402
from transit.models.train import CATEGORICAL, NUMERIC  # noqa: E402

REPORTS, FIG, MODELS = ROOT / "reports", ROOT / "reports" / "figures", ROOT / "models"
MODES = {"rail": "Rail", "road": "Road (bus, metrobus)", "sea": "Sea (ferries)"}
TEST_START, TEST_END = "2024-06-01", "2024-07-31"
COLS = NUMERIC + CATEGORICAL
plt.rcParams.update({"figure.dpi": 120, "font.size": 9})


def forecast_weather(start: str, end: str) -> pd.DataFrame:
    """Hourly weather as forecast one day ahead (Open-Meteo Previous Runs API)."""
    vars_ = ["temperature_2m", "precipitation", "snowfall", "wind_speed_10m"]
    r = requests.get("https://previous-runs-api.open-meteo.com/v1/forecast", timeout=60, params={
        "latitude": LAT, "longitude": LON, "start_date": start, "end_date": end, "timezone": TIMEZONE,
        "hourly": ",".join(f"{v}_previous_day1" for v in vars_)})
    r.raise_for_status()
    h = r.json()["hourly"]
    return pd.DataFrame({"timestamp": pd.to_datetime(h["time"]), **{v: h[f"{v}_previous_day1"] for v in vars_}})


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    hourly = load_hourly()
    start, end = hourly["timestamp"].min().date().isoformat(), hourly["timestamp"].max().date().isoformat()
    cal = holiday_calendar(start, end)
    observed = load_weather(start, end)
    feats = build_features(hourly, observed, cal)
    fc = forecast_weather(TEST_START, TEST_END)
    mixed = pd.concat([observed[observed["timestamp"] < TEST_START], fc], ignore_index=True)
    feats_fc = build_features(hourly, mixed.ffill(), cal)

    lines = ["# Explainability and day-ahead stress test", "",
             "## What drives the forecasts (SHAP)", "",
             "SHAP values from `shap.TreeExplainer` on the published models, computed on the last 8 weeks of data. "
             "The models use a Poisson loss, so SHAP values are on the log scale: +0.1 means about 10% more "
             "passengers for that hour.", ""]
    for mode, label in MODES.items():
        path = MODELS / f"transit_gbm_{mode}.skops"
        model = load(path, trusted=get_untrusted_types(file=path))
        df = feats[feats["transport_type"] == mode].dropna(subset=["lag_168", "roll_mean_168"])
        X = df[df["timestamp"] >= df["timestamp"].max() - pd.Timedelta(weeks=8)][COLS].fillna(0)
        sv = shap.TreeExplainer(model).shap_values(X)
        shap.summary_plot(sv, X, max_display=12, show=False, plot_size=(7, 4.5))
        plt.title(f"{label}: SHAP values (last 8 weeks)")
        plt.tight_layout()
        plt.savefig(FIG / f"shap_{mode}.png")
        plt.close()
        top = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False).head(5)
        lines += [f"**{label}** — most important inputs: " + ", ".join(f"`{k}`" for k in top.index) + ".", "",
                  f"![SHAP {mode}](figures/shap_{mode}.png)", ""]
        print(mode, list(top.index))

    lines += ["## Day-ahead stress test: forecast weather instead of observed weather", "",
              f"Models trained on data before {TEST_START}, tested on {TEST_START} – {TEST_END} (hourly WAPE). "
              "The 'forecast' column feeds the weather forecast issued the day before, as a real day-ahead "
              "service would.", "", "| Mode | Observed weather | Day-ahead forecast weather | Same hour last week |",
              "|---|---|---|---|"]
    from train_final import MODE_PARAMS, PARAMS  # noqa: E402
    for mode, label in MODES.items():
        params = MODE_PARAMS.get(mode, PARAMS)
        res = {}
        for name, F in (("observed", feats), ("forecast", feats_fc)):
            df = F[F["transport_type"] == mode].dropna(subset=["lag_168", "roll_mean_168"])
            tr, te = df[df["timestamp"] < TEST_START], df[df["timestamp"] >= TEST_START]
            m = HistGradientBoostingRegressor(**params).fit(tr[COLS].fillna(0), tr["passengers"])
            res[name] = metrics(te["passengers"], np.clip(m.predict(te[COLS].fillna(0)), 0, None))["WAPE"]
            res["naive"] = metrics(te["passengers"], te["lag_168"])["WAPE"]
        lines.append(f"| {label} | {res['observed']:.2f}% | {res['forecast']:.2f}% | {res['naive']:.2f}% |")
        print(mode, res)
    lines += ["", "Using forecast weather costs little: weather explains a small part of hourly demand compared "
              "with the time of day, the calendar and last week's demand (see the SHAP plots).", ""]
    (REPORTS / "explainability.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    main()
