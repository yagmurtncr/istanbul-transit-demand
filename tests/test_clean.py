import pandas as pd

from transit.data.clean import load_raw, to_hourly


def test_load_and_aggregate(tmp_path, raw_df):
    p = tmp_path / "m.csv"
    raw_df.to_csv(p, index=False)
    df = load_raw(p)
    assert {"date", "hour", "transport_type_id", "passengers"} <= set(df.columns)

    hourly = to_hourly(df)
    assert hourly.groupby("transport_type").size().nunique() == 1          # same length per group
    assert hourly["passengers"].sum() == raw_df["number_of_passenger"].clip(lower=0).sum()


def test_missing_hours_filled_with_zero(raw_df):
    df = raw_df.rename(columns={"transition_date": "date", "transition_hour": "hour",
                                "number_of_passenger": "passengers"})
    df = df[~((df["date"] == "2024-03-05") & (df["hour"] == 3))]
    hourly = to_hourly(df)
    gap = hourly[hourly["timestamp"] == pd.Timestamp("2024-03-05 03:00")]
    assert len(gap) == 2 and (gap["passengers"] == 0).all()
