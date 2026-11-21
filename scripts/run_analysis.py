"""Phase 2-3 on real data: EDA figures, statistical tests and model comparison.

Reads the pre-aggregated İBB data in data/aggregated/, adds weather and holidays, and writes
reports/results.md plus figures in reports/figures/. Runs locally or in GitHub Actions.

    python scripts/run_analysis.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from transit.analysis.stats import daily_table, holiday_effect, rain_effect  # noqa: E402
from transit.config import ROOT  # noqa: E402
from transit.data.aggregated import load_hourly  # noqa: E402
from transit.data.external import fetch_weather, holiday_calendar  # noqa: E402
from transit.features.build import build_features  # noqa: E402
from transit.models.train import compare, predictions_for_plot, summary  # noqa: E402

REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"
MODES = {"rail": "Rail (metro, Marmaray, tram)", "road": "Road (bus, metrobus)", "sea": "Sea (ferries)"}
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})


def fmt_effect(e: dict) -> str:
    sig = "significant" if e["p_value"] < 0.05 else "not significant"
    return (f"{e['pct_diff']:+.1f}% (95% CI {e['ci_low']:+.1f}% to {e['ci_high']:+.1f}%, "
            f"p={e['p_value']:.3f}, {sig}; n={e['n_treated']} vs {e['n_control']})")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    hourly = load_hourly()
    start, end = hourly["timestamp"].min().date().isoformat(), hourly["timestamp"].max().date().isoformat()
    print(f"hourly rows: {len(hourly):,}  ({start} -> {end})")
    weather, cal = fetch_weather(start, end), holiday_calendar(start, end)
    feats = build_features(hourly, weather, cal)
    daily = daily_table(hourly, weather, cal)

    # ---------- EDA figures ----------
    h = hourly.assign(hour=hourly["timestamp"].dt.hour, weekend=hourly["timestamp"].dt.dayofweek >= 5)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.2))
    for ax, (mode, label) in zip(axes, MODES.items(), strict=True):
        p = h[h["transport_type"] == mode].groupby(["weekend", "hour"])["passengers"].mean().unstack(0)
        ax.plot(p.index, p[False] / 1e3, label="Weekday")
        ax.plot(p.index, p[True] / 1e3, label="Weekend", linestyle="--")
        ax.set_title(label)
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Avg passengers (thousands)")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(FIG / "hourly_profile.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 3.4))
    for mode, label in MODES.items():
        s = daily[daily["transport_type"] == mode].set_index("date")["passengers"] / 1e6
        ax.plot(s.index, s.values, label=label, linewidth=1)
    for dday in daily.loc[daily["is_holiday"] == 1, "date"].unique():
        ax.axvspan(dday, dday + pd.Timedelta(days=1), color="orange", alpha=0.25, linewidth=0)
    ax.set_ylabel("Passengers per day (millions)")
    ax.set_title("Daily passengers by mode — public holidays shaded")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "daily_series.png")
    plt.close(fig)

    # ---------- statistics ----------
    effects = {}
    for mode in ("rail", "road", "sea"):
        effects[(mode, "rain")] = rain_effect(daily, mode)
        effects[(mode, "holiday")] = holiday_effect(daily, mode)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    labels, vals, lo, hi = [], [], [], []
    for (mode, kind), e in effects.items():
        labels.append(f"{mode} · {kind}")
        vals.append(e["pct_diff"])
        lo.append(e["pct_diff"] - e["ci_low"])
        hi.append(e["ci_high"] - e["pct_diff"])
    ax.barh(labels, vals, xerr=[lo, hi], color=["#1a73e8" if "rain" in lb else "#f0a500" for lb in labels])
    ax.axvline(0, color="#333", linewidth=0.8)
    ax.set_xlabel("% change vs ordinary weekday (95% bootstrap CI)")
    fig.tight_layout()
    fig.savefig(FIG / "effects.png")
    plt.close(fig)

    # ---------- models ----------
    model_tables, importances = {}, {}
    for mode in ("rail", "road"):
        res, imp = compare(feats, mode)
        model_tables[mode] = summary(res)
        importances[mode] = imp
        print(f"\n== {mode} ==\n{model_tables[mode]}")
    pred = predictions_for_plot(feats, "rail")
    fig, ax = plt.subplots(figsize=(12, 3.2))
    ax.plot(pred["timestamp"], pred["actual"] / 1e3, label="Actual", linewidth=1)
    ax.plot(pred["timestamp"], pred["predicted"] / 1e3, label="Forecast (gradient boosting)", linewidth=1)
    ax.set_ylabel("Rail passengers per hour (thousands)")
    ax.set_title("Rail: last 14 days, out-of-sample")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "forecast_rail.png")
    plt.close(fig)
    imp = importances["rail"]
    if imp is not None:
        top = imp.head(10)[::-1]
        fig, ax = plt.subplots(figsize=(6, 3.2))
        ax.barh(top["feature"], top["importance"])
        ax.set_xlabel("Permutation importance (MAE increase)")
        ax.set_title(f"Rail — what drives the {imp.attrs.get('model', '')} forecast")
        fig.tight_layout()
        fig.savefig(FIG / "importance_rail.png")
        plt.close(fig)

    # ---------- report ----------
    tot = daily.groupby("transport_type")["passengers"].sum()
    lines = [
        "# Results (İBB data, January–July 2024)", "",
        f"Data: {len(hourly):,} hourly rows, {daily['date'].nunique()} days, "
        f"{tot.sum() / 1e9:.2f} billion recorded passengers "
        f"(rail {tot.get('rail', 0) / 1e6:,.0f} M, road {tot.get('road', 0) / 1e6:,.0f} M, sea {tot.get('sea', 0) / 1e6:,.0f} M).",
        "Weather: Open-Meteo hourly archive for central Istanbul. Holidays: `holidays` package (incl. eves).", "",
        "## Demand patterns", "", "![Hourly profile](figures/hourly_profile.png)", "",
        "![Daily series](figures/daily_series.png)", "",
        "## Statistical tests", "",
        "Working days only (Mon–Fri, excluding holiday eves). Rainy day = at least 2 mm of rain between 06:00 and 22:00; "
        "dry day = under 0.2 mm. Percentile bootstrap (5,000 resamples) and two-sided Mann-Whitney U test.", "",
        "| Mode | Rain effect | Public-holiday effect |", "|---|---|---|",
    ]
    for mode in ("rail", "road", "sea"):
        lines.append(f"| {mode} | {fmt_effect(effects[(mode, 'rain')])} | {fmt_effect(effects[(mode, 'holiday')])} |")
    lines += ["", "![Effects](figures/effects.png)", "", "## Forecasting (hourly, day-ahead features)", "",
              "Expanding-window walk-forward validation, 4 folds × 14 days. All lag features end at least 24 h "
              "before the forecast hour (enforced by a unit test).", ""]
    for mode, t in model_tables.items():
        lines += [f"### {MODES[mode]}", "", t.to_markdown(), ""]
    lines += ["![Forecast](figures/forecast_rail.png)", "", "![Importance](figures/importance_rail.png)", ""]
    (REPORTS / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nEffects:")
    for (mode, kind), e in effects.items():
        print(f"  {mode:5s} {kind:8s} {fmt_effect(e)}")
    print(f"\nwrote {REPORTS / 'results.md'}")


if __name__ == "__main__":
    main()
