"""Load raw İBB CSVs and aggregate them into a clean hourly demand table."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from transit.config import TRANSPORT_TYPES

# Raw files are not always consistent: normalise known column-name variants.
RENAME = {
    "transition_date": "date",
    "transition_hour": "hour",
    "line_name": "line",
    "number_of_passage": "passages",
    "number_of_passenger": "passengers",
}
REQUIRED = ["date", "hour", "transport_type_id", "passengers"]


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})
    df = df.loc[:, ~df.columns.duplicated()]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}; got {list(df.columns)}")
    return df


def to_hourly(df: pd.DataFrame, by: tuple[str, ...] = ("transport_type",)) -> pd.DataFrame:
    """Aggregate passengers to one row per timestamp (and group); hours with no record become 0."""
    out = df.copy()
    out["hour"] = pd.to_numeric(out["hour"], errors="coerce")
    out["passengers"] = pd.to_numeric(out["passengers"], errors="coerce")
    out = out.dropna(subset=["date", "hour", "passengers"])
    out = out[(out["hour"] >= 0) & (out["hour"] <= 23) & (out["passengers"] >= 0)]
    out["timestamp"] = (pd.to_datetime(out["date"]).dt.normalize()
                        + pd.to_timedelta(out["hour"].astype(int), unit="h"))
    out["transport_type"] = pd.to_numeric(out["transport_type_id"], errors="coerce").map(TRANSPORT_TYPES).fillna("other")

    keys = ["timestamp", *by]
    agg = out.groupby(keys, as_index=False)["passengers"].sum()
    full_index = pd.MultiIndex.from_product(
        [pd.date_range(agg["timestamp"].min(), agg["timestamp"].max(), freq="h")]
        + [sorted(agg[c].unique()) for c in by],
        names=keys,
    )
    return agg.set_index(keys).reindex(full_index, fill_value=0).reset_index()


def build_hourly(paths: list[Path], by: tuple[str, ...] = ("transport_type",)) -> pd.DataFrame:
    return to_hourly(pd.concat([load_raw(p) for p in paths], ignore_index=True), by=by)
