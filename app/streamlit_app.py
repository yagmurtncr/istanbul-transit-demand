"""Istanbul public transport demand — interactive backtest dashboard.

    pip install -e ".[app]"
    streamlit run app/streamlit_app.py

Pick a mode and a day: the model is trained only on data before that day and forecasts
all 24 hours, so you can compare the forecast with what actually happened.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # works without `pip install -e .`

from transit.data.aggregated import load_hourly
from transit.data.external import holiday_calendar, load_weather
from transit.features.build import build_features
from transit.models.baseline import metrics
from transit.models.train import CATEGORICAL, NUMERIC

MODES = {"rail": "Rail (metro, Marmaray, tram)", "road": "Road (bus, metrobus)", "sea": "Sea (ferries)"}
st.set_page_config(page_title="Istanbul transit demand", page_icon="🚇", layout="wide")


@st.cache_data(show_spinner="Loading İBB data and weather…")
def load() -> pd.DataFrame:
    hourly = load_hourly()
    start, end = hourly["timestamp"].min().date().isoformat(), hourly["timestamp"].max().date().isoformat()
    return build_features(hourly, load_weather(start, end), holiday_calendar(start, end))


@st.cache_data(show_spinner="Training on data before the selected day…")
def forecast(feats: pd.DataFrame, mode: str, day: pd.Timestamp) -> pd.DataFrame:
    df = feats[feats["transport_type"] == mode].dropna(subset=["lag_168", "roll_mean_168"])
    train, test = df[df["timestamp"] < day], df[df["timestamp"].dt.normalize() == day]
    model = HistGradientBoostingRegressor(loss="poisson", max_iter=400, learning_rate=0.05, random_state=0)
    model.fit(train[NUMERIC + CATEGORICAL].fillna(0), train["passengers"])
    out = test[["timestamp", "passengers", "lag_168"]].copy()
    out["forecast"] = model.predict(test[NUMERIC + CATEGORICAL].fillna(0)).clip(min=0)
    return out


feats = load()
st.title("🚇 Istanbul public transport demand")
st.caption("İBB open data, January 2022 – July 2024 · gradient boosting (Poisson loss) with weather, holidays and school breaks")

c1, c2 = st.columns([1, 2])
mode = c1.selectbox("Mode", list(MODES), format_func=MODES.get)
days = sorted(feats["timestamp"].dt.normalize().unique())
day = c2.select_slider("Day to forecast", options=days[60:], value=days[-1],
                       format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b %Y"))
day = pd.Timestamp(day)

res = forecast(feats, mode, day)
info = feats[(feats["timestamp"].dt.normalize() == day)].iloc[0]
flags = [label for col, label in (("is_holiday", "public holiday"), ("is_eve", "holiday eve"),
                                  ("school_closed", "school break"), ("is_weekend", "weekend")) if info.get(col) == 1]
rain = feats[(feats["timestamp"].dt.normalize() == day) & feats["timestamp"].dt.hour.between(6, 21)]["precipitation"].sum()

m_model, m_naive = metrics(res["passengers"], res["forecast"]), metrics(res["passengers"], res["lag_168"])
k1, k2, k3, k4 = st.columns(4)
k1.metric("Actual passengers", f"{res['passengers'].sum() / 1e6:.2f} M")
k2.metric("Forecast", f"{res['forecast'].sum() / 1e6:.2f} M",
          f"{(res['forecast'].sum() / res['passengers'].sum() - 1) * 100:+.1f}%")
k3.metric("Hourly error (WAPE)", f"{m_model['WAPE']:.1f}%",
          f"{m_model['WAPE'] - m_naive['WAPE']:+.1f} pts vs last week", delta_color="inverse")
k4.metric("Day type", ", ".join(flags) or "working day", f"rain {rain:.1f} mm", delta_color="off")

fig = go.Figure()
fig.add_bar(x=res["timestamp"].dt.hour, y=res["passengers"], name="Actual", marker_color="#c7d7f5")
fig.add_scatter(x=res["timestamp"].dt.hour, y=res["forecast"], name="Forecast", mode="lines+markers",
                line={"color": "#1a73e8", "width": 3})
fig.add_scatter(x=res["timestamp"].dt.hour, y=res["lag_168"], name="Same hour last week", mode="lines",
                line={"color": "#999", "dash": "dot"})
fig.update_layout(xaxis_title="Hour of day", yaxis_title="Passengers", height=420, legend={"orientation": "h"},
                  margin={"t": 10})
try:
    st.plotly_chart(fig, width="stretch")
except TypeError:  # older Streamlit (e.g. the in-browser build)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("**How it works:** the model is retrained on every hour before the selected day and predicts all 24 hours "
            "using only information available a day ahead (lagged demand, calendar, holidays, school breaks, weather). "
            "Full analysis: [reports/results.md](https://github.com/yagmurtncr/istanbul-transit-demand/blob/main/reports/results.md)")
