import numpy as np
import pandas as pd

from transit.data.clean import to_hourly
from transit.data.external import holiday_calendar
from transit.features.build import build_features


def _hourly(raw_df):
    df = raw_df.rename(columns={"transition_date": "date", "transition_hour": "hour",
                                "number_of_passenger": "passengers"})
    return to_hourly(df)


def test_lags_do_not_leak_future(raw_df):
    """Changing future values must not change any feature of an earlier row."""
    hourly = _hourly(raw_df)
    cutoff = pd.Timestamp("2024-04-01")
    a = build_features(hourly, None, None)
    tampered = hourly.copy()
    tampered.loc[tampered["timestamp"] >= cutoff, "passengers"] *= 100
    b = build_features(tampered, None, None)
    feat_cols = [c for c in a.columns if c.startswith(("lag_", "roll_"))]
    past = a["timestamp"] < cutoff + pd.Timedelta(hours=24)
    pd.testing.assert_frame_equal(a.loc[past, feat_cols], b.loc[past, feat_cols])


def test_lag_168_is_last_week(raw_df):
    f = build_features(_hourly(raw_df), None, None)
    s = f[f["transport_type"] == "road"].set_index("timestamp")
    t = pd.Timestamp("2024-03-20 08:00")
    assert s.loc[t, "lag_168"] == s.loc[t - pd.Timedelta(hours=168), "passengers"]


def test_holiday_calendar_marks_bayram_and_eve():
    cal = holiday_calendar("2024-04-01", "2024-04-30").set_index("date")
    assert cal.loc["2024-04-10", "is_holiday"] == 1      # Ramazan Bayramı, day 1
    assert cal.loc["2024-04-09", "is_eve"] == 1          # arife
    assert cal.loc["2024-04-20", "is_holiday"] == 0
    assert np.issubdtype(cal["is_holiday"].dtype, np.integer)


def test_school_calendar():
    cal = holiday_calendar("2024-06-10", "2024-06-20").set_index("date")
    assert cal.loc["2024-06-14", "school_closed"] == 0      # last school day
    assert cal.loc["2024-06-17", "school_closed"] == 1      # summer break


def test_bridge_and_election_days():
    cal = holiday_calendar("2023-05-01", "2023-06-30").set_index("date")
    assert cal.loc["2023-05-14", "is_election"] == 1
    assert cal.loc["2023-06-26", "is_bridge"] == 1
    assert cal.loc["2023-06-26", "is_holiday"] == 0


def test_earthquake_extended_school_break():
    cal = holiday_calendar("2023-02-01", "2023-02-28").set_index("date")
    assert cal.loc["2023-02-15", "school_closed"] == 1
    assert cal.loc["2023-02-20", "school_closed"] == 0


def test_holiday_types_ramadan_and_half_days():
    cal = holiday_calendar("2024-01-01", "2024-12-31").set_index("date")
    assert cal.loc["2024-04-23", "is_national_holiday"] == 1      # 23 Nisan
    assert cal.loc["2024-07-15", "is_national_holiday"] == 1      # 15 Temmuz
    assert cal.loc["2024-06-17", "is_religious_holiday"] == 1     # Kurban Bayramı
    assert cal.loc["2024-10-28", "is_half_day"] == 1
    assert cal.loc["2024-03-20", "is_ramadan"] == 1 and cal.loc["2024-05-20", "is_ramadan"] == 0
