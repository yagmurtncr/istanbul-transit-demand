"""Simple, plain-language figures for the README (English and Turkish versions).

    python scripts/readme_figures.py

Writes reports/figures/readme/{name}_{en,tr}.png. Used by the Analysis workflow.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transit.analysis.stats import daily_table, holiday_effect, rain_effect, school_break_effect  # noqa: E402
from transit.data.aggregated import load_hourly  # noqa: E402
from transit.data.external import holiday_calendar, load_weather  # noqa: E402
from transit.features.build import build_features  # noqa: E402
from transit.models.baseline import metrics  # noqa: E402
from transit.models.train import CATEGORICAL, NUMERIC  # noqa: E402

OUT = ROOT / "reports" / "figures" / "readme"
BLUE, ORANGE, AQUA, GRAY = "#257de0", "#f47230", "#00b894", "#9c9c9c"
INK, INK2 = "#191919", "#666666"
MODE_COLOR = {"rail": BLUE, "road": ORANGE, "sea": AQUA}
HOLIDAYS = ["2024-04-10", "2024-04-23", "2024-06-17"]

T = {
    "en": {
        "profile_title": "A typical weekday in Istanbul: two rush hours",
        "profile_y": "Average passengers per hour",
        "profile_x": "Hour of day",
        "rail": "Rail (metro, Marmaray, tram)", "road": "Road (bus, metrobus)", "sea": "Sea (ferries)",
        "morning": "Morning rush", "evening": "Evening rush",
        "effects_title": "What changes demand? Change vs an ordinary weekday",
        "holiday": "Public holiday", "school": "School break", "rain": "Rainy day (≥ 2 mm)",
        "test_title": "Holidays: how far off is each forecast? (rail + road, hourly error)",
        "rule": "\"Same hour last week\" rule", "model": "This project's model",
        "days": {"2024-04-10": "10 Apr 2024\nRamazan Bayramı", "2024-04-23": "23 Apr 2024\nNational holiday",
                 "2024-06-17": "17 Jun 2024\nKurban Bayramı"},
        "lower": "lower is better",
    },
    "tr": {
        "profile_title": "İstanbul'da sıradan bir hafta içi günü: iki yoğun saat",
        "profile_y": "Saatte ortalama yolcu",
        "profile_x": "Günün saati",
        "rail": "Raylı sistem (metro, Marmaray, tramvay)", "road": "Karayolu (otobüs, metrobüs)",
        "sea": "Deniz (vapur)",
        "morning": "Sabah yoğunluğu", "evening": "Akşam yoğunluğu",
        "effects_title": "Talebi ne değiştiriyor? Sıradan bir hafta içi gününe göre değişim",
        "holiday": "Resmi tatil", "school": "Okul tatili", "rain": "Yağmurlu gün (≥ 2 mm)",
        "test_title": "Tatillerde tahminler ne kadar yanılıyor? (raylı + karayolu, saatlik hata)",
        "rule": "\"Geçen hafta aynı saat\" kuralı", "model": "Bu projenin modeli",
        "days": {"2024-04-10": "10 Nisan 2024\nRamazan Bayramı", "2024-04-23": "23 Nisan 2024\nUlusal bayram",
                 "2024-06-17": "17 Haziran 2024\nKurban Bayramı"},
        "lower": "düşük olan daha iyi",
    },
}


def style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#cccccc")
    ax.tick_params(colors=INK2, labelsize=10)
    ax.grid(axis="y", color="#eeeeee", linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name: str, lang: str) -> None:
    fig.savefig(OUT / f"{name}_{lang}.png", dpi=150, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def day_profile(hourly: pd.DataFrame, lang: str) -> None:
    t = T[lang]
    h = hourly[hourly["timestamp"].dt.day_of_week < 5]
    p = h.assign(hour=h["timestamp"].dt.hour).groupby(["transport_type", "hour"])["passengers"].mean().unstack(0)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for mode in ("rail", "road"):
        ax.plot(p.index, p[mode] / 1e3, color=MODE_COLOR[mode], linewidth=2.5, label=t[mode])
    for hours, key in (((7, 8), "morning"), ((18,), "evening")):
        y = p.loc[list(hours), ["rail", "road"]].max().max() / 1e3
        ax.annotate(t[key], (sum(hours) / len(hours), y), xytext=(0, 10), textcoords="offset points", ha="center",
                    fontsize=10, color=INK, fontweight="bold")
    ax.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}k")
    ax.set_xlabel(t["profile_x"], color=INK2)
    ax.set_ylabel(t["profile_y"], color=INK2)
    ax.set_ylim(0, p[["rail", "road"]].max().max() / 1e3 * 1.2)
    ax.set_title(t["profile_title"], loc="left", fontsize=13, color=INK, fontweight="bold")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=10)
    style(ax)
    save(fig, "day_profile", lang)


def effects(daily: pd.DataFrame, lang: str) -> None:
    t = T[lang]
    kinds = [("holiday", holiday_effect), ("school", school_break_effect), ("rain", rain_effect)]
    vals = {m: [fn(daily, m)["pct_diff"] for _, fn in kinds] for m in ("rail", "road", "sea")}
    fig, ax = plt.subplots(figsize=(9, 4.4))
    y = np.arange(len(kinds))
    hgt = 0.26
    for i, mode in enumerate(("rail", "road", "sea")):
        pos = y + (i - 1) * (hgt + 0.02)
        bars = ax.barh(pos, vals[mode], height=hgt, color=MODE_COLOR[mode], label=t[mode])
        for b, v in zip(bars, vals[mode], strict=True):
            ax.text(v + (2 if v >= 0 else -2), b.get_y() + b.get_height() / 2, f"{v:+.0f}%",
                    va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK)
    ax.axvline(0, color="#888888", linewidth=1)
    ax.set_yticks(y, [t[k] for k, _ in kinds], fontsize=11, color=INK)
    ax.invert_yaxis()
    lo, hi = min(min(v) for v in vals.values()), max(max(v) for v in vals.values())
    ax.set_xlim(lo - 15, hi + 20)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}%")
    ax.set_title(t["effects_title"], loc="left", fontsize=13, color=INK, fontweight="bold")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#eeeeee", linewidth=0.8)
    save(fig, "what_changes_demand", lang)


def holiday_errors(feats: pd.DataFrame) -> dict[str, tuple[float, float]]:
    out = {}
    for d in HOLIDAYS:
        day = pd.Timestamp(d)
        actual, rule, model_pred = [], [], []
        for mode in ("rail", "road"):
            df = feats[feats["transport_type"] == mode].dropna(subset=["lag_168", "roll_mean_168"])
            train, test = df[df["timestamp"] < day], df[df["timestamp"].dt.normalize() == day]
            m = HistGradientBoostingRegressor(loss="poisson", max_iter=400, learning_rate=0.05, random_state=0)
            m.fit(train[NUMERIC + CATEGORICAL].fillna(0), train["passengers"])
            actual += list(test["passengers"])
            rule += list(test["lag_168"])
            model_pred += list(m.predict(test[NUMERIC + CATEGORICAL].fillna(0)).clip(min=0))
        out[d] = (metrics(actual, rule)["WAPE"], metrics(actual, model_pred)["WAPE"])
    return out


def holiday_test(errs: dict[str, tuple[float, float]], lang: str) -> None:
    t = T[lang]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(HOLIDAYS))
    w = 0.36
    for i, (label, color) in enumerate(((t["rule"], GRAY), (t["model"], BLUE))):
        v = [errs[d][i] for d in HOLIDAYS]
        bars = ax.bar(x + (i - 0.5) * (w + 0.03), v, width=w, color=color, label=label)
        for b, val in zip(bars, v, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, val + 1.2, f"{val:.0f}%", ha="center", fontsize=10,
                    color=INK, fontweight="bold" if i == 1 else "normal")
    ax.set_xticks(x, [t["days"][d] for d in HOLIDAYS], fontsize=10, color=INK)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_ylim(0, max(max(e) for e in errs.values()) * 1.15)
    ax.set_title(t["test_title"] + "\n", loc="left", fontsize=13, color=INK, fontweight="bold")
    ax.text(0.0, 1.03, t["lower"], transform=ax.transAxes, ha="left", va="bottom", fontsize=10, color=INK2)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=10)
    style(ax)
    save(fig, "holiday_test", lang)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hourly = load_hourly()
    start, end = hourly["timestamp"].min().date().isoformat(), hourly["timestamp"].max().date().isoformat()
    weather, cal = load_weather(start, end), holiday_calendar(start, end)
    daily = daily_table(hourly, weather, cal)
    errs = holiday_errors(build_features(hourly, weather, cal))
    for lang in T:
        day_profile(hourly, lang)
        effects(daily, lang)
        holiday_test(errs, lang)
    print("holiday errors (rule, model):", {d: tuple(round(v, 1) for v in e) for d, e in errs.items()})


if __name__ == "__main__":
    main()
