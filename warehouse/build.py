"""Build the DuckDB warehouse (data/warehouse.duckdb) from the aggregated İBB extracts in data/detail/.

    python warehouse/build.py            # build, run quality checks, export marts to reports/warehouse/

Layers: staging views -> dimensions -> facts -> marts, then data-quality checks (warehouse/sql/*.sql).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transit.data.external import holiday_calendar  # noqa: E402

SQL = ROOT / "warehouse" / "sql"
DETAIL = ROOT / "data" / "detail"
DB = ROOT / "data" / "warehouse.duckdb"
EXPORT = ROOT / "reports" / "warehouse"
MARTS = ["mart_monthly_kpis", "mart_mode_share", "mart_line_ranking_2023", "mart_station_ranking_2023",
         "mart_district_2023", "mart_fare_mix_monthly", "mart_peak_load_2023", "mart_line_daytype_effect",
         "mart_transfer_rate", "dim_month_quality"]


def run_file(con: duckdb.DuckDBPyConnection, path: Path, detail: Path) -> None:
    con.execute(path.read_text(encoding="utf-8").replace("{DETAIL}", detail.as_posix()))


def load_dim_date(con: duckdb.DuckDBPyConnection) -> None:
    start, end = con.execute("SELECT MIN(date), MAX(date) FROM stg_hourly").fetchall()[0]
    cal = holiday_calendar(str(start), str(end))
    cal["day_of_week"] = cal["date"].dt.day_of_week
    cal["is_weekend"] = (cal["day_of_week"] >= 5).astype(int)
    con.register("cal_df", cal)
    con.execute("CREATE OR REPLACE TABLE dim_date AS SELECT CAST(date AS DATE) AS date, * EXCLUDE (date) FROM cal_df")


def quality_checks(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    text = (SQL / "05_quality_checks.sql").read_text(encoding="utf-8")
    results = {}
    for name, query in re.findall(r"-- name: (\w+)\n(.*?);", text, flags=re.S):
        results[name] = len(con.execute(query).fetchall())
    return results


def build(detail: Path = DETAIL, db: Path = DB, export: Path | None = EXPORT) -> dict[str, int]:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    run_file(con, SQL / "01_staging.sql", detail)
    load_dim_date(con)
    for f in ("02_dimensions.sql", "03_facts.sql", "04_marts.sql"):
        run_file(con, SQL / f, detail)
    checks = quality_checks(con)
    if export:
        export.mkdir(parents=True, exist_ok=True)
        for t in MARTS:
            con.execute(f"SELECT * FROM {t}").df().to_csv(export / f"{t}.csv", index=False)
    con.close()
    return checks


if __name__ == "__main__":
    checks = build()
    failed = {k: v for k, v in checks.items() if v}
    for k, v in checks.items():
        print(f"{'PASS' if not v else 'FAIL'}  {k}" + (f"  ({v} rows)" if v else ""))
    if failed:
        sys.exit(1)
    print(f"\nwarehouse: {DB}\nmarts exported to {EXPORT}")
