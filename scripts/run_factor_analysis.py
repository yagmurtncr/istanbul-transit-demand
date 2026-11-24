"""Which factors move Istanbul's transit demand, and by how much?

Distributions by day type, Spearman correlations, year-over-year change, the Ramadan evening
shift, and a multivariate regression that estimates each factor's effect while holding the
others fixed (weekday, month, year, weather, every calendar flag). Writes reports/factors.md.

    python scripts/run_factor_analysis.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

from transit.config import ROOT  # noqa: E402
from transit.data.aggregated import load_hourly  # noqa: E402
from transit.data.external import holiday_calendar, load_weather  # noqa: E402

REPORTS, FIG = ROOT / "reports", ROOT / "reports" / "figures"
MODES = {"rail": "Rail", "road": "Road (bus, metrobus)", "sea": "Sea (ferries)"}
FLAGS = ["is_religious_holiday", "is_national_holiday", "is_half_day", "is_bridge", "school_closed",
         "is_ramadan", "is_election"]
LABELS = {"is_religious_holiday": "Religious holiday (bayram)", "is_national_holiday": "National holiday",
          "is_half_day": "Half day (arife, 28 Ekim)", "is_bridge": "Bridge day (idari izin)",
          "school_closed": "School break", "is_ramadan": "Ramadan", "is_election": "Election day",
          "rain_mm": "Rain, per 10 mm", "temp": "Temperature, per +10 °C"}
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})


def day_type(r) -> str:
    if r.is_religious_holiday:
        return "Religious holiday"
    if r.is_national_holiday:
        return "National holiday"
    if r.is_bridge:
        return "Bridge day"
    if r.is_half_day:
        return "Half day"
    if r.dow == 6:
        return "Sunday"
    if r.dow == 5:
        return "Saturday"
    return "Weekday, school break" if r.school_closed else "Weekday, term time"


def daily_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    hourly = load_hourly()
    start, end = hourly["timestamp"].min().date().isoformat(), hourly["timestamp"].max().date().isoformat()
    w = load_weather(start, end)
    w = w[w["timestamp"].dt.hour.between(6, 21)].assign(date=lambda d: d["timestamp"].dt.normalize())
    wd = w.groupby("date", as_index=False).agg(rain_mm=("precipitation", "sum"), temp=("temperature_2m", "mean"),
                                               wind=("wind_speed_10m", "mean"))
    d = (hourly.assign(date=hourly["timestamp"].dt.normalize())
         .groupby(["date", "transport_type"], as_index=False)["passengers"].sum())
    d = d.merge(wd, on="date", how="left").merge(holiday_calendar(start, end), on="date", how="left")
    d["dow"], d["month"], d["year"] = d["date"].dt.day_of_week, d["date"].dt.month, d["date"].dt.year
    d["day_type"] = d.apply(day_type, axis=1)
    return d, hourly


def regression(d: pd.DataFrame, mode: str) -> pd.DataFrame:
    x = d[d["transport_type"] == mode].copy()
    x["log_p"] = np.log(x["passengers"].clip(lower=1))
    x["rain10"], x["temp10"] = x["rain_mm"] / 10, x["temp"] / 10
    years = "+ C(year)" if x["year"].nunique() > 1 else ""
    formula = f"log_p ~ C(dow) + C(month) {years} + rain10 + temp10 + " + " + ".join(FLAGS)
    m = smf.ols(formula, data=x).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    rows = []
    for term, label in [*[(f, LABELS[f]) for f in FLAGS], ("rain10", LABELS["rain_mm"]), ("temp10", LABELS["temp"])]:
        if term not in m.params or x[term].abs().sum() == 0:
            continue
        lo, hi = m.conf_int().loc[term]
        rows.append({"factor": label, "effect_%": (np.exp(m.params[term]) - 1) * 100,
                     "ci_low": (np.exp(lo) - 1) * 100, "ci_high": (np.exp(hi) - 1) * 100,
                     "p": m.pvalues[term], "days": int((x[term] != 0).sum()) if term in FLAGS else len(x)})
    out = pd.DataFrame(rows)
    out.attrs["r2"] = m.rsquared
    return out


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    d, hourly = daily_frame()
    lines = ["# Factors behind Istanbul transit demand", "",
             f"{d['date'].nunique()} days ({d['date'].min():%d %b %Y} – {d['date'].max():%d %b %Y}), "
             f"{d['passengers'].sum() / 1e9:.2f} billion passengers.", ""]

    # 1. monthly volume and year-over-year change
    mon = d.groupby([pd.Grouper(key="date", freq="MS"), "transport_type"])["passengers"].sum().unstack()
    fig, ax = plt.subplots(figsize=(12, 3.2))
    for mode, label in MODES.items():
        if mode in mon:
            ax.plot(mon.index, mon[mode] / 1e6, label=label, marker="o", markersize=3)
    ax.set_ylabel("Passengers per month (millions)")
    ax.set_title("Monthly demand by mode")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "factors_monthly.png")
    plt.close(fig)
    lines += ["## Monthly demand", "", "![Monthly](figures/factors_monthly.png)", ""]
    if d["year"].nunique() > 1:
        yoy = (d.groupby(["year", "month", "transport_type"])["passengers"].sum().unstack("year")
               .pipe(lambda t: t.pct_change(axis=1) * 100).iloc[:, 1:].groupby("transport_type").mean().round(1))
        lines += ["Average year-over-year change of monthly volume (%):", "", yoy.to_markdown(), ""]

    # 2. distribution by day type
    order = ["Weekday, term time", "Weekday, school break", "Half day", "Bridge day", "Saturday", "Sunday",
             "National holiday", "Religious holiday"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharey=False)
    for ax, (mode, label) in zip(axes, MODES.items(), strict=True):
        x = d[d["transport_type"] == mode]
        data = [x.loc[x["day_type"] == t, "passengers"] / 1e6 for t in order]
        ax.boxplot(data, showfliers=False)
        ax.set_xticks(range(1, len(order) + 1), [t.replace(", ", "\n") for t in order])
        ax.tick_params(axis="x", rotation=60, labelsize=7)
        ax.set_title(label)
        ax.set_ylabel("Passengers per day (millions)")
    fig.tight_layout()
    fig.savefig(FIG / "factors_daytype.png")
    plt.close(fig)
    med = (d.groupby(["day_type", "transport_type"])["passengers"].median().unstack() / 1e6).reindex(order).round(2)
    med["days"] = d[d["transport_type"] == "rail"].groupby("day_type").size().reindex(order)
    lines += ["## Distribution by day type", "", "![Day types](figures/factors_daytype.png)", "",
              "Median passengers per day (millions):", "", med.to_markdown(), ""]

    # 3. Spearman correlations
    piv = d.pivot_table(index="date", columns="transport_type", values="passengers")
    cal = d.drop_duplicates("date").set_index("date")[["temp", "rain_mm", "wind", *FLAGS]]
    corr = pd.concat([piv, cal], axis=1).corr(method="spearman").loc[list(cal.columns), list(piv.columns)].dropna(how="all")
    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-0.6, vmax=0.6)
    ax.set_xticks(range(len(corr.columns)), corr.columns)
    ax.set_yticks(range(len(corr.index)), [LABELS.get(i, i) for i in corr.index])
    for (i, j), v in np.ndenumerate(corr.values):
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Spearman correlation with daily passengers")
    fig.tight_layout()
    fig.savefig(FIG / "factors_correlation.png")
    plt.close(fig)
    lines += ["## Correlations", "",
              "Raw (unadjusted) Spearman correlations. They mix effects together: for example school breaks "
              "fall in warm months, so temperature and school breaks look alike. The regression below separates them.",
              "", "![Correlation](figures/factors_correlation.png)", ""]

    # 4. Ramadan evening shift (rail, weekdays in term time)
    h = hourly[hourly["transport_type"] == "rail"].assign(date=lambda t: t["timestamp"].dt.normalize(),
                                                          hour=lambda t: t["timestamp"].dt.hour)
    h = h.merge(d.drop_duplicates("date")[["date", "dow", "is_ramadan", "is_holiday", "school_closed"]], on="date")
    h = h[(h["dow"] < 5) & (h["is_holiday"] == 0) & (h["school_closed"] == 0)]
    if h["is_ramadan"].nunique() == 2:
        prof = h.groupby(["is_ramadan", "hour"])["passengers"].mean().unstack(0)
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.plot(prof.index, prof[0] / 1e3, label="Other weekdays")
        ax.plot(prof.index, prof[1] / 1e3, label="Ramadan weekdays")
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Rail passengers per hour (thousands)")
        ax.legend()
        ax.set_title("Ramadan shifts the evening peak (rail, term-time weekdays)")
        fig.tight_layout()
        fig.savefig(FIG / "factors_ramadan.png")
        plt.close(fig)
        diff = ((prof[1] / prof[0] - 1) * 100).round(1)
        lines += ["## Ramadan", "", "![Ramadan](figures/factors_ramadan.png)", "",
                  f"Largest drop: {diff.min():+.1f}% at {int(diff.idxmin()):02d}:00 (around iftar); "
                  f"largest rise: {diff.max():+.1f}% at {int(diff.idxmax()):02d}:00.", ""]

    # 5. multivariate regression
    lines += ["## Effect of each factor, holding the others fixed", "",
              "OLS on log daily passengers with weekday, month and year fixed effects, rain, temperature and every "
              "calendar flag; Newey-West (HAC) standard errors. Effects are % change vs an otherwise identical day.", ""]
    for mode, label in MODES.items():
        reg = regression(d, mode)
        fmt = reg.copy()
        fmt["effect (95% CI)"] = [f"{e:+.1f}% ({lo:+.1f} to {hi:+.1f})"
                                  for e, lo, hi in zip(reg["effect_%"], reg["ci_low"], reg["ci_high"], strict=True)]
        fmt["p"] = reg["p"].map(lambda p: "<0.001" if p < 0.001 else f"{p:.3f}")
        lines += [f"### {label} (R² = {reg.attrs['r2']:.2f})", "",
                  fmt[["factor", "effect (95% CI)", "p", "days"]].to_markdown(index=False), ""]
        print(f"\n== {label} (R2 {reg.attrs['r2']:.2f}) ==\n" + fmt[["factor", "effect (95% CI)", "p", "days"]].to_string(index=False))
    (REPORTS / "factors.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {REPORTS / 'factors.md'}")


if __name__ == "__main__":
    main()
