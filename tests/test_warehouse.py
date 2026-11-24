"""Build the warehouse on a small synthetic extract and check that every data-quality rule passes."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

duckdb = pytest.importorskip("duckdb")
ROOT = Path(__file__).resolve().parents[1]


def _write_detail(folder: Path) -> None:
    rng = np.random.default_rng(0)
    days = list(pd.date_range("2020-01-01", "2020-02-29")) + list(pd.date_range("2023-01-01", "2023-02-28"))
    rows = []
    lines = [(1, "34", "AVCILAR-ZINCIRLIKUYU", "AVCILAR"), (2, "M1A", "YENIKAPI-HAVALIMANI", "BAKIRKOY"),
             (3, "KAD", "KADIKOY-KARAKOY", "KADIKOY")]
    for d in days:
        for mode, code, route, town in lines:
            for h in range(6, 23):
                for kind, ttype, transfer in (("TAM", "Tam Kontur", "Normal"), ("INDIRIMLI1", "Indirimli Abonman", "Aktarma")):
                    pe = int(rng.integers(50, 500))
                    rows.append((d.date().isoformat(), h, mode, code, route, town, f"{code}-ST", kind, ttype, transfer,
                                 pe + int(rng.integers(0, 20)), pe))
    raw = pd.DataFrame(rows, columns=["date", "hour", "transport_type_id", "line_code", "route", "district", "station",
                                      "product_kind", "transaction_type", "transfer_type", "passages", "passengers"])
    s = ["passages", "passengers"]
    raw.groupby(["date", "hour", "transport_type_id"], as_index=False)[s].sum().to_csv(folder / "hourly_mode.csv.gz", index=False)
    raw.groupby(["date", "transport_type_id", "line_code", "route"], as_index=False)[s].sum().to_csv(folder / "line_daily.csv.gz", index=False)
    raw.groupby(["date", "transport_type_id", "station", "line_code"], as_index=False)[s].sum().to_csv(folder / "station_daily.csv.gz", index=False)
    raw.groupby(["date", "transport_type_id", "district"], as_index=False)[s].sum().to_csv(folder / "district_daily.csv.gz", index=False)
    raw.groupby(["date", "transport_type_id", "product_kind", "transaction_type", "transfer_type"], as_index=False)[s].sum() \
        .to_csv(folder / "fare_daily.csv.gz", index=False)
    lh = raw.assign(year=pd.to_datetime(raw["date"]).dt.year, is_weekend=(pd.to_datetime(raw["date"]).dt.day_of_week >= 5).astype(int))
    lh.groupby(["year", "transport_type_id", "line_code", "hour", "is_weekend"], as_index=False)[s].sum() \
        .to_csv(folder / "line_hour_profile.csv.gz", index=False)


def test_warehouse_builds_and_passes_quality_checks(tmp_path):
    spec = importlib.util.spec_from_file_location("build", ROOT / "warehouse" / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    _write_detail(tmp_path)
    checks = build.build(detail=tmp_path, db=tmp_path / "wh.duckdb", export=tmp_path / "out")
    assert checks and all(v == 0 for v in checks.values()), checks
    ranking = pd.read_csv(tmp_path / "out" / "mart_line_ranking_2023.csv")
    assert set(ranking["line_code"]) == {"34", "M1A", "KAD"}
    kpis = pd.read_csv(tmp_path / "out" / "mart_monthly_kpis.csv")
    assert kpis["recovery_index"].notna().all()
