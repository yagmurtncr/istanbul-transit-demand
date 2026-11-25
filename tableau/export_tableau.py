"""Export Tableau-ready tables from the DuckDB warehouse into one Excel workbook.

    python warehouse/build.py && python tableau/export_tableau.py

Writes tableau/istanbul_transit_tableau.xlsx: one sheet per table, tidy (long) format, readable
column names, plus a 'README' sheet that describes every field. Open it in Tableau Public
(Connect > Microsoft Excel) and relate the sheets on their shared fields.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "warehouse.duckdb"
OUT = ROOT / "tableau" / "istanbul_transit_tableau.xlsx"
MODE = "CASE mode_id WHEN 1 THEN 'Road' WHEN 2 THEN 'Rail' ELSE 'Sea' END"

QUERIES = {
    "monthly_kpis": (f"""
        SELECT k.month AS "Month", {MODE} AS "Mode", k.passengers AS "Passengers",
               ROUND(k.avg_daily_passengers) AS "Avg daily passengers", ROUND(k.recovery_index, 1) AS "Recovery index (%)",
               ROUND(k.yoy_pct, 1) AS "YoY change (%)", k.is_complete AS "Complete month", k.is_covid_period AS "Covid period"
        FROM mart_monthly_kpis k ORDER BY 1, 2""",
        "Monthly passengers per mode. Recovery index = average daily passengers vs Jan-Feb 2020 (=100)."),
    "daily": (f"""
        SELECT d.date AS "Date", {MODE} AS "Mode", d.passengers AS "Passengers", d.passages AS "Boardings",
               CASE WHEN c.is_religious_holiday = 1 THEN 'Religious holiday' WHEN c.is_bridge = 1 THEN 'Bridge day'
                    WHEN c.is_national_holiday = 1 THEN 'National holiday' WHEN c.is_half_day = 1 THEN 'Half day'
                    WHEN c.day_of_week = 6 THEN 'Sunday' WHEN c.day_of_week = 5 THEN 'Saturday'
                    WHEN c.school_closed = 1 THEN 'Weekday, school break' ELSE 'Weekday, term time' END AS "Day type",
               c.holiday_name AS "Holiday", c.is_ramadan AS "Ramadan", c.is_election AS "Election day"
        FROM fct_daily_mode d JOIN dim_date c USING (date) ORDER BY 1, 2""",
        "Daily passengers and boardings per mode with the day type from the Turkish calendar."),
    "hourly_profile": (f"""
        SELECT year(date) AS "Year", {MODE} AS "Mode", hour AS "Hour",
               CASE WHEN dayofweek(date) IN (0, 6) THEN 'Weekend' ELSE 'Weekday' END AS "Day kind",
               ROUND(AVG(passengers)) AS "Avg passengers"
        FROM fct_hourly_ridership GROUP BY ALL ORDER BY 1, 2, 4, 3""",
        "Average passengers per hour of the day, by year, mode and weekday/weekend."),
    "line_monthly": (f"""
        SELECT date_trunc('month', f.date) AS "Month", {MODE} AS "Mode", f.line_code AS "Line", l.route AS "Route",
               SUM(f.passengers) AS "Passengers"
        FROM fct_line_daily f JOIN dim_line l USING (line_code, mode_id) GROUP BY ALL ORDER BY 1, 5 DESC""",
        "Monthly passengers per line (line code and main route)."),
    "line_peak_2023": ("""
        SELECT line_code AS "Line", route AS "Route", split_part(mode_label, ' (', 1) AS "Mode", peak_hour AS "Peak hour",
               ROUND(peak_hour_passengers) AS "Peak hour passengers (avg weekday)",
               ROUND(weekday_passengers) AS "Weekday passengers (avg)", ROUND(peak_share_pct, 1) AS "Peak share of day (%)"
        FROM mart_peak_load_2023 WHERE weekday_passengers >= 1000 ORDER BY 5 DESC""",
        "Capacity: each line's busiest weekday hour in 2023."),
    "line_hour_2023": (f"""
        SELECT p.line_code AS "Line", {MODE} AS "Mode", p.hour AS "Hour",
               CASE WHEN p.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS "Day kind", p.passengers AS "Passengers (2023 total)"
        FROM fct_line_hour_profile p JOIN (SELECT line_code, mode_id FROM mart_peak_load_2023 ORDER BY peak_hour_passengers DESC LIMIT 40) t
             USING (line_code, mode_id)
        WHERE p.year = 2023 ORDER BY 1, 4, 3""",
        "Hour-by-hour passengers in 2023 for the 40 lines with the heaviest peak hour (for a heatmap)."),
    "stations_2023": ("""
        SELECT rank AS "Rank", station AS "Station", split_part(mode_label, ' (', 1) AS "Mode", main_line AS "Main line",
               passengers AS "Passengers 2023"
        FROM mart_station_ranking_2023 ORDER BY 1""",
        "Stations ranked by passengers in 2023 (rail and metrobus stations)."),
    "districts_2023": ("""
        SELECT district AS "District", passengers AS "Passengers 2023", ROUND(share_pct, 2) AS "Share (%)",
               ROUND(rail_share_pct, 1) AS "Rail share (%)"
        FROM mart_district_2023 ORDER BY 2 DESC""",
        "Rail and ferry boardings by district in 2023 (bus districts are not reliable in the source)."),
    "fare_mix": ("""
        SELECT f.month AS "Month", f.card_group AS "Card group", f.payment_type AS "Payment type",
               f.passengers AS "Passengers", ROUND(f.share_pct, 2) AS "Share (%)"
        FROM mart_fare_mix_monthly f JOIN dim_month_quality q USING (month) WHERE q.is_complete ORDER BY 1, 4 DESC""",
        "Monthly passengers by card group and payment type (complete months only)."),
    "special_days": ("""
        SELECT line_code AS "Line", route AS "Route", split_part(mode_label, ' (', 1) AS "Mode", day_type AS "Day type",
               days AS "Days", ROUND(avg_passengers) AS "Avg passengers", ROUND(ordinary_weekday) AS "Ordinary weekday",
               ROUND(change_pct, 1) AS "Change vs ordinary weekday (%)"
        FROM mart_line_daytype_effect WHERE days >= 3 AND ordinary_weekday >= 10000 ORDER BY 4, 8""",
        "How each line's demand changes on special days (lines with 10,000+ ordinary weekday passengers)."),
}


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    frames = {name: con.execute(sql).df() for name, (sql, _) in QUERIES.items()}
    con.close()
    readme = pd.DataFrame([{"Sheet": n, "Rows": len(frames[n]), "Description": d} for n, (_, d) in QUERIES.items()])
    note = pd.DataFrame([{"Sheet": "", "Rows": None, "Description":
                          "Source: IBB Acik Veri Portali, Saatlik Toplu Ulasim Veri Seti (IBB Open Data License), Jan 2020 - "
                          "Oct 2024; Aug-Oct 2024 are partially published. Built by github.com/yagmurtncr/istanbul-transit-demand"}])
    OUT.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        pd.concat([readme, note]).to_excel(xw, sheet_name="README", index=False)
        for name, df in frames.items():
            df.to_excel(xw, sheet_name=name, index=False)
        for ws in xw.book.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    cell.font = Font(name="Arial", bold=cell.row == 1)
            for i, col in enumerate(ws.columns, 1):
                width = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:200])
                ws.column_dimensions[get_column_letter(i)].width = min(max(10, width + 2), 60)
            ws.freeze_panes = "A2"
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB): " + ", ".join(f"{n} {len(f):,}" for n, f in frames.items()))


if __name__ == "__main__":
    main()
