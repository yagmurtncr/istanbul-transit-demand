import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def raw_df():
    """Synthetic data in the İBB raw format: 6 weeks, 2 transport types, daily + weekly seasonality."""
    rng = np.random.default_rng(0)
    rows = []
    for d in pd.date_range("2024-03-01", periods=42, freq="D"):
        for h in range(24):
            for t in (1, 2):
                base = 1000 * t * (1.5 if 7 <= h <= 9 or 17 <= h <= 19 else 0.6) * (0.7 if d.day_of_week >= 5 else 1)
                for line in ("A", "B"):
                    rows.append({"transition_date": d.date().isoformat(), "transition_hour": h,
                                 "transport_type_id": t, "line_name": line,
                                 "number_of_passenger": int(base / 2 + rng.normal(0, 20))})
    return pd.DataFrame(rows)
