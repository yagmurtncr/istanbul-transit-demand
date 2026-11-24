"""Turn the warehouse marts into decisions: capacity, pricing and operations.

Reads reports/warehouse/*.csv (written by warehouse/build.py) and writes
reports/business_insights.md plus figures in reports/figures/business/.

    python warehouse/build.py && python scripts/business_report.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "reports" / "warehouse"
FIG = ROOT / "reports" / "figures" / "business"
OUT = ROOT / "reports" / "business_insights.md"
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})


def m(name: str) -> pd.DataFrame:
    return pd.read_csv(MARTS / f"{name}.csv")


def fmt_m(x: float) -> str:
    return f"{x / 1e6:,.1f} M"


def save(fig, name: str) -> str:
    fig.tight_layout()
    fig.savefig(FIG / name)
    plt.close(fig)
    return f"figures/business/{name}"


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    L = ["# Business insights: Istanbul public transport", "",
         "What the İBB ridership data means for **capacity**, **pricing** and **operations**. Every number comes from "
         "the DuckDB warehouse (`warehouse/`), complete months only; Covid-19 months and partially published months "
         "(Aug–Oct 2024) are flagged in `dim_month_quality`.", ""]

    # --- Network health -------------------------------------------------------------------------------
    k = m("mart_monthly_kpis")
    k["month"] = pd.to_datetime(k["month"])
    kc = k[k["is_complete"]]
    tot = kc.groupby("month")["passengers"].sum()
    y = tot.groupby(tot.index.year).sum()
    days = tot.groupby(tot.index.year).size()
    full = y[days == 12] if (days == 12).any() else y  # prefer complete years
    last = full.index.max()
    ndays = kc[kc["month"].dt.year == last].groupby("month")["avg_daily_passengers"].sum()
    fig, ax = plt.subplots(figsize=(11, 3.2))
    for mode, g in kc.groupby("mode_id"):
        ax.plot(g["month"], g["recovery_index"], label={1: "Road", 2: "Rail", 3: "Sea"}[mode])
    ax.axhline(100, color="#999", linestyle=":")
    ax.set_ylabel("% of Jan–Feb 2020 daily level")
    ax.set_title("Recovery index: daily passengers vs pre-pandemic level")
    ax.legend()
    img = save(fig, "recovery_index.png")
    growth = (full / full.shift(1) - 1) * 100
    L += ["## 1. Network health", "",
          f"- **{last}:** {full[last] / 1e9:.2f} billion passengers, {ndays.mean() / 1e6:.2f} million per day"
          + (f", **{growth[last]:+.1f}%** vs {last - 1}." if pd.notna(growth.get(last)) else "."),
          f"- Lowest point: **{k['recovery_index'].min():.0f}%** of the pre-pandemic level "
          f"({k.loc[k['recovery_index'].idxmin(), 'month']:%B %Y})."]
    rec = kc[kc["month"].dt.year == last].groupby("mode_id")["recovery_index"].mean()
    names = {1: "buses and metrobus", 2: "rail", 3: "ferries"}
    L += [f"- **Recovery in {last}** vs the January–February 2020 daily level: "
          + ", ".join(f"{names[i]} **{v:.0f}%**" for i, v in rec.items()) + ". "
          + ("Rail and ferries are above the pre-pandemic level while road transport is still below it: part of the "
             "demand has moved to rail, which gained new lines in this period."
             if rec.get(2, 0) > 100 and rec.get(1, 100) < 100 else "")]
    L += ["", f"![Recovery]({img})", ""]

    # --- Capacity -------------------------------------------------------------------------------------
    lines = m("mart_line_ranking_2023").sort_values("rank").head(10)
    peak = m("mart_peak_load_2023").sort_values("peak_hour_passengers", ascending=False)
    stations = m("mart_station_ranking_2023").sort_values("rank").head(10)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.barh(lines["line_code"].astype(str) + " " + lines["route"].str.slice(0, 28), lines["passengers"] / 1e6)
    ax.invert_yaxis()
    ax.set_xlabel("Passengers in 2023 (millions)")
    ax.set_title("Busiest lines, 2023")
    img_l = save(fig, "top_lines.png")
    top_peak = peak.head(10)
    L += ["## 2. Capacity: where and when the network is stretched", "",
          f"- The 10 busiest lines carry **{lines['passengers'].sum() / m('mart_line_ranking_2023')['passengers'].sum() * 100:.0f}%** "
          f"of all boardings; #1 is **{lines.iloc[0]['line_code']} {lines.iloc[0]['route']}** with {fmt_m(lines.iloc[0]['passengers'])}.",
          f"- Busiest station: **{stations.iloc[0]['station']}** ({fmt_m(stations.iloc[0]['passengers'])} in 2023).",
          "- **Peak-hour load** is what sizes fleets and headways. The lines with the heaviest single weekday hour:", "",
          "| Line | Route | Mode | Peak hour | Passengers in peak hour (avg weekday) | Share of the day in that hour |",
          "|---|---|---|---|---|---|"]
    for _, r in top_peak.iterrows():
        L.append(f"| {r['line_code']} | {r['route']} | {r['mode_label'].split(' (')[0]} | {int(r['peak_hour']):02d}:00 | "
                 f"{r['peak_hour_passengers']:,.0f} | {r['peak_share_pct']:.1f}% |")
    peaky = peak[peak["weekday_passengers"] > 20000].sort_values("peak_share_pct", ascending=False).head(5)
    L += ["", f"**Decision:** lines whose peak hour holds an unusually large share of the day "
          f"({', '.join(peaky['line_code'].astype(str))}) gain most from extra peak-only trips or short-turn services, "
          "rather than all-day frequency increases.", "", f"![Top lines]({img_l})", ""]

    # --- Pricing --------------------------------------------------------------------------------------
    fm = m("mart_fare_mix_monthly")
    fm["month"] = pd.to_datetime(fm["month"])
    q = m("dim_month_quality")
    fm = fm[fm["month"].isin(pd.to_datetime(q.loc[q["is_complete"], "month"]))]
    cg = fm.groupby(["month", "card_group"])["share_pct"].sum().unstack().fillna(0)
    fig, ax = plt.subplots(figsize=(11, 3.2))
    for c in cg.columns:
        ax.plot(cg.index, cg[c], label=c)
    ax.set_ylabel("% of passengers")
    ax.set_title("Card groups over time")
    ax.legend(ncol=3, fontsize=8)
    img_f = save(fig, "fare_mix.png")
    y23 = fm[fm["month"].dt.year == 2023]
    cg23 = y23.groupby("card_group")["passengers"].sum() / y23["passengers"].sum() * 100
    pt23 = y23.groupby("payment_type")["passengers"].sum() / y23["passengers"].sum() * 100
    L += ["## 3. Pricing: who pays what", "",
          "2023 boardings by card group: " + ", ".join(f"{k} {v:.0f}%" for k, v in cg23.sort_values(ascending=False).items())
          + ".", "", "By payment type: " + ", ".join(f"{k} {v:.0f}%" for k, v in pt23.sort_values(ascending=False).items())
          + ".", ""]
    d1 = cg.get("Discounted type 1")
    L += ["- The fare codes are reported as published: İBB does not say which concession each discounted code "
          "covers, and code 1 alone is over 40% of boardings, so it cannot be students only."]
    covid = pd.to_datetime(q.loc[q["is_covid_period"], "month"])
    d1 = d1[~d1.index.isin(covid)] if d1 is not None else None
    if d1 is not None and len(d1) > 24:
        jump = d1.diff().idxmax()
        after = d1[d1.index >= jump].mean()
        L += [f"- The biggest month-to-month shift in the mix: discounted type 1 went from {d1.shift(1)[jump]:.0f}% to "
              f"{d1[jump]:.0f}% of boardings in {jump:%B %Y} (average {after:.0f}% afterwards). A step like this points to a "
              "change in fare rules or card eligibility; revenue models should not mix months from before and after it."]
    tr = m("mart_transfer_rate")
    tr23 = tr[tr["year"] == 2023].set_index("mode_label")["transfer_pct"]
    if len(tr23):
        L += ["- **Transfers:** " + ", ".join(f"{k.split(' (')[0]} {v:.0f}%" for k, v in tr23.items())
              + " of boardings are discounted transfers; any change to the transfer rule hits these riders first."]
    L += ["", f"![Fare mix]({img_f})", ""]

    # --- Operations -----------------------------------------------------------------------------------
    eff = m("mart_line_daytype_effect")
    eff = eff[(eff["days"] >= 3) & (eff["ordinary_weekday"] >= 10000)]  # lines with real weekday demand
    L += ["## 4. Operations: planning for special days", "",
          "Change vs an ordinary weekday on the same line, for lines with at least 10,000 weekday passengers "
          "(weekdays only, complete months after the pandemic):", "",
          "| Day type | Median line | Lines that drop most | Lines that rise most |", "|---|---|---|---|"]
    for dt_, g in eff.groupby("day_type"):
        lo = g.nsmallest(3, "change_pct")
        hi = g.nlargest(3, "change_pct")
        L.append(f"| {dt_} | {g['change_pct'].median():+.0f}% | "
                 + ", ".join(f"{r.line_code} ({r.change_pct:+.0f}%)" for r in lo.itertuples()) + " | "
                 + ", ".join(f"{r.line_code} ({r.change_pct:+.0f}%)" for r in hi.itertuples()) + " |")
    L += ["", "**Decisions:**",
          "- **Bridge days** (idari izin) behave like a holiday on commuter lines: run a Saturday-type timetable on "
          "the lines in the 'drop most' column instead of a full weekday service.",
          "- **Religious holidays** move demand to ferries and leisure routes: shift vehicles from commuter lines "
          "to the 'rise most' lines rather than cutting the whole network.",
          "- **School breaks** lower weekday demand across the network; the lines that drop most are the natural "
          "candidates for maintenance closures and reduced timetables in those weeks.",
          "- Statistical effects of rain, temperature, Ramadan, elections and every holiday type are in "
          "[`factors.md`](factors.md); day-ahead forecasts are in [`results.md`](results.md).", ""]

    # --- Districts ------------------------------------------------------------------------------------
    dist = m("mart_district_2023").sort_values("passengers", ascending=False)
    dist = dist[dist["district"] != "UNKNOWN"]
    fig, ax = plt.subplots(figsize=(7, 4))
    top = dist.head(15)
    ax.barh(top["district"], top["share_pct"])
    ax.invert_yaxis()
    ax.set_xlabel("% of rail and ferry boardings, 2023")
    ax.set_title("Rail and ferry boardings by district")
    img_d = save(fig, "districts.png")
    L += ["## 5. Districts (rail and ferries)", "",
          "Rail stations and ferry piers have a fixed district, so they show where trips start. Bus boardings are left "
          "out: 55% of them are recorded under Bakırköy, which reflects how the data is registered, not where people "
          "board.", "",
          f"- The top 5 districts hold **{dist.head(5)['share_pct'].sum():.0f}%** of rail and ferry boardings: "
          + ", ".join(f"{r.district} {r.share_pct:.1f}%" for r in dist.head(5).itertuples()) + ".",
          "", f"![Districts]({img_d})", ""]

    OUT.write_text("\n".join(x for x in L if x is not None), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
