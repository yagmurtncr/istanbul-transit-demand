"""Phase 1: download -> clean -> enrich -> features -> baseline scores.

Usage:
    python scripts/run_phase1.py --months 12
    python scripts/run_phase1.py --skip-download      # reuse files already in data/raw
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from transit.config import PROCESSED, RAW
from transit.data import clean, external, ibb
from transit.features.build import build_features
from transit.models.baseline import metrics, seasonal_naive, walk_forward


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=12, help="download the most recent N monthly files")
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    if args.skip_download:
        paths = sorted(RAW.glob("*.csv"))
    else:
        res = ibb.list_resources()
        print(f"{len(res)} monthly files on the portal; downloading the last {args.months}")
        paths = ibb.download(res[-args.months:])
    if not paths:
        sys.exit("No CSV files in data/raw. Run without --skip-download first.")

    hourly = clean.build_hourly(paths)
    start = hourly["timestamp"].min().date().isoformat()
    end = hourly["timestamp"].max().date().isoformat()
    print(f"hourly table: {len(hourly):,} rows, {start} -> {end}")

    feats = build_features(hourly, external.fetch_weather(start, end), external.holiday_calendar(start, end))
    PROCESSED.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(PROCESSED / "features.parquet", index=False)

    scored = feats.dropna(subset=["lag_168"]).reset_index(drop=True)
    rows = [{"fold": i, **metrics(scored.iloc[te]["passengers"], seasonal_naive(scored.iloc[te]))}
            for i, (_, te) in enumerate(walk_forward(scored["timestamp"]), 1)]
    print("\nSeasonal-naive baseline (same hour last week), walk-forward:")
    print(pd.DataFrame(rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
