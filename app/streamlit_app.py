"""Istanbul public transport demand — interactive backtest dashboard.

    pip install -e ".[app]"
    streamlit run app/streamlit_app.py

Two views:
- Future day: forecast any day after the data ends (e.g. tomorrow) from calendar, holidays,
  school breaks and weather. No actual counts exist yet, so it is an estimate.
- Check a past day: the model is trained only on data before that day and forecasts all 24 hours,
  so you can compare the forecast with what actually happened.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # works without `pip install -e .`

from transit.data.aggregated import load_hourly
from transit.data.external import holiday_calendar, load_weather
from transit.features.build import add_calendar, build_features
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


# Day-ahead model without lagged demand: works for any future date, at the cost of accuracy.
FUTURE_FEATURES = ["t", "hour", "dow", "month", "is_weekend", "hour_sin", "hour_cos", "temperature_2m",
                   "precipitation", "wind_speed_10m", "is_holiday", "is_religious_holiday", "is_national_holiday",
                   "is_eve", "is_half_day", "is_ramadan", "is_bridge", "is_election", "school_closed"]
WEATHER_COLS = ["temperature_2m", "precipitation", "wind_speed_10m"]
EPOCH = pd.Timestamp("2022-01-01")
# Hourly WAPE of this model when trained on 2022-2023 and tested on Jan-Jul 2024 with average weather.
FUTURE_WAPE = {"rail": 10.6, "road": 12.1, "sea": 16.3}


@st.cache_resource(show_spinner="Training the future-day model…")
def future_model(feats: pd.DataFrame, mode: str) -> HistGradientBoostingRegressor:
    df = feats[feats["transport_type"] == mode].assign(t=lambda d: (d["timestamp"] - EPOCH).dt.days)
    model = HistGradientBoostingRegressor(loss="poisson", max_iter=400, learning_rate=0.05, random_state=0)
    return model.fit(df[FUTURE_FEATURES].fillna(0), df["passengers"])


def weather_for(day: pd.Timestamp, feats: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Open-Meteo forecast when the day is within its 16-day horizon, else the 2022-2024 hourly average."""
    hours = pd.date_range(day, periods=24, freq="h")
    if 0 <= (day.date() - dt.date.today()).days <= 15:
        url = ("https://api.open-meteo.com/v1/forecast?latitude=41.01&longitude=28.97&timezone=Europe%2FIstanbul"
               f"&hourly={','.join(WEATHER_COLS)}&start_date={day.date()}&end_date={day.date()}")
        try:
            try:
                from pyodide.http import open_url  # in-browser build
                import json
                data = json.loads(open_url(url).read())
            except ImportError:
                import requests
                data = requests.get(url, timeout=20).json()
            wx = pd.DataFrame(data["hourly"]).rename(columns={"time": "timestamp"})
            wx["timestamp"] = pd.to_datetime(wx["timestamp"])
            if len(wx) == 24 and wx[WEATHER_COLS].notna().all().all():
                return wx, "Open-Meteo forecast"
        except Exception:
            pass
    clim = (feats.drop_duplicates("timestamp").assign(month=lambda d: d["timestamp"].dt.month)
            .groupby(["month", "hour"])[WEATHER_COLS].mean())
    wx = pd.DataFrame({"timestamp": hours, "hour": hours.hour})
    wx = wx.merge(clim.loc[day.month].reset_index(), on="hour", how="left")[["timestamp"] + WEATHER_COLS]
    return wx, f"average {day.strftime('%B')} weather (2022-2024)"


def future_frame(day: pd.Timestamp, wx: pd.DataFrame) -> pd.DataFrame:
    df = add_calendar(pd.DataFrame({"timestamp": pd.date_range(day, periods=24, freq="h")}))
    cal = holiday_calendar(day.date().isoformat(), day.date().isoformat())
    df = df.merge(wx, on="timestamp", how="left").merge(cal, on="date", how="left")
    df["t"] = (df["timestamp"] - EPOCH).dt.days
    return df


def plot(fig: go.Figure) -> None:
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:  # older Streamlit (e.g. the in-browser build)
        st.plotly_chart(fig, use_container_width=True)


def day_flags(row) -> list[str]:
    flags = [label for col, label in (("is_holiday", "public holiday"), ("is_eve", "holiday eve"),
                                      ("school_closed", "school break"), ("is_ramadan", "Ramadan"),
                                      ("is_weekend", "weekend")) if row.get(col) == 1]
    name = str(row.get("holiday_name") or "")
    return [f"{flags[0]} ({name})"] + flags[1:] if name and flags and flags[0] == "public holiday" else flags


feats = load()
st.title("🚇 Istanbul public transport demand")
st.caption("İBB open data, January 2022 – July 2024 · gradient boosting (Poisson loss) with weather, holidays and school breaks")

tab_en, tab_tr = st.tabs(["English", "Türkçe"])
tab_en.markdown(
    "**Why this exists.** Istanbul's rail, bus and ferry networks carry millions of trips a day, and demand swings "
    "sharply with the hour, the weather, holidays and school breaks. Operators have to decide a day ahead how many "
    "trains, buses and ferries to run and how many staff to schedule; the usual rule of thumb is *\"expect what we "
    "saw at the same hour last week\"*, which breaks down exactly on the unusual days that matter most.\n\n"
    "**What it does.** It forecasts hourly passengers with machine learning, in two views:\n"
    "- **🔮 Future day:** pick any date (tomorrow by default) and get its 24-hour forecast from the calendar, "
    "holidays, school breaks and the weather forecast.\n"
    "- **🔍 Check a past day:** pick a day between 2022 and 2024. The model trains only on data *before* that day "
    "and its forecast is shown next to the real İBB counts and the last-week rule, so you can see how accurate it is.\n\n"
    "**How to use:** choose a view, a transport mode (Mode) and a date.\n\n"
    "**Tip:** in *Check a past day*, pick **10 April 2024** (Ramazan Bayramı) or **23 April 2024**. The last-week "
    "rule goes badly wrong on these holidays, the model does not. For a rainy day, try **29 November 2023**: "
    "on ferries you will see the model miss too."
)
tab_tr.markdown(
    "**Neden var?** İstanbul'da raylı sistemler, otobüsler ve vapurlar günde milyonlarca yolcu taşıyor ve talep "
    "saate, havaya, resmi tatillere ve okul tatillerine göre ciddi şekilde değişiyor. İşletmeler kaç sefer yapılacağına "
    "ve kaç personel çalıştırılacağına bir gün önceden karar vermek zorunda. Genelde kullanılan kural "
    "*\"geçen hafta aynı saatte ne olduysa yine o olur\"*; ama bu kural tam da önemli olan sıra dışı günlerde yanılıyor.\n\n"
    "**Ne yapıyor?** Saatlik yolcu sayısını makine öğrenmesiyle tahmin ediyor. İki görünüm var:\n"
    "- **🔮 Future day (gelecek gün):** İstediğin bir tarihi seç (varsayılan: yarın). Model takvim, resmi tatiller, "
    "okul tatilleri ve hava tahminiyle o günün 24 saatini tahmin eder.\n"
    "- **🔍 Check a past day (geçmiş günü test et):** 2022-2024 arasından bir gün seç. Model yalnızca o günden *önceki* "
    "verilerle eğitilir ve tahmini gerçek İBB sayıları ve \"geçen hafta\" kuralıyla yan yana gösterilir. Böylece modelin "
    "ne kadar isabetli olduğunu görebilirsin.\n\n"
    "**Nasıl kullanılır?** Bir görünüm, bir ulaşım türü (Mode) ve bir tarih seç.\n\n"
    "**İpucu:** *Check a past day* görünümünde **10 Nisan 2024** (Ramazan Bayramı) veya **23 Nisan 2024**'ü seç. "
    "\"Geçen hafta\" kuralı bu tatillerde çok yanılır, model ise yakalar. Yağmurlu bir gün için **29 Kasım 2023**'e bak: "
    "vapurlarda modelin de yanıldığını göreceksin."
)

view = st.radio("View", ["🔮 Future day", "🔍 Check a past day"], horizontal=True, label_visibility="collapsed")
c1, c2 = st.columns([1, 2])
mode = c1.selectbox("Mode", list(MODES), format_func=MODES.get)
last_day = feats["timestamp"].max().normalize()

if view.startswith("🔮"):
    tomorrow = (pd.Timestamp.now("UTC").tz_convert(None) + pd.Timedelta(hours=3 + 24)).normalize()  # Istanbul = UTC+3
    first, last = last_day + pd.Timedelta(days=1), pd.Timestamp("2027-06-30")
    pick = c2.date_input("Day to forecast", value=min(max(tomorrow, first), last).date(),
                         min_value=first.date(), max_value=last.date())
    day = pd.Timestamp(pick)
    wx, wx_source = weather_for(day, feats)
    X = future_frame(day, wx)
    X["forecast"] = future_model(feats, mode).predict(X[FUTURE_FEATURES].fillna(0)).clip(min=0)

    st.subheader(f"Forecast for {day.strftime('%A, %d %B %Y')} · {MODES[mode]}")
    st.caption(f"Estimate from calendar, holidays, school breaks and {wx_source}. "
               "This day has not happened yet (or is not in the data), so there is no actual count to compare with.")
    peak = X.loc[X["forecast"].idxmax()]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Forecast passengers", f"{X['forecast'].sum() / 1e6:.2f} M")
    k2.metric("Busiest hour", f"{int(peak['hour']):02d}:00", f"{peak['forecast'] / 1e3:,.0f}k passengers", delta_color="off")
    k3.metric("Typical hourly error", f"±{FUTURE_WAPE[mode]:.0f}%", "tested on Jan-Jul 2024", delta_color="off")
    k4.metric("Day type", ", ".join(day_flags(X.iloc[0])) or "working day",
              f"rain {X.loc[X['hour'].between(6, 21), 'precipitation'].sum():.1f} mm", delta_color="off")

    fig = go.Figure()
    fig.add_bar(x=X["hour"], y=X["forecast"], name="Forecast", marker_color="#1a73e8")
    fig.update_layout(xaxis_title=f"Hour of day ({day.strftime('%a %d %b %Y')})", yaxis_title="Passengers",
                      height=420, margin={"t": 10})
    plot(fig)
    st.info(f"**Read with care.** The İBB data in this demo ends on {last_day.strftime('%d %B %Y')}. New lines "
            "opened and ridership grew since then, which the model cannot see, so real numbers are probably higher. "
            "Use it for the *shape* of the day (peaks, holiday and rain effects) more than the exact total. "
            "To see how accurate the method is on days with known results, switch to **🔍 Check a past day**.")
else:
    days = sorted(feats["timestamp"].dt.normalize().unique())
    day = c2.select_slider("Day to forecast", options=days[60:], value=days[-1],
                           format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b %Y"))
    day = pd.Timestamp(day)

    res = forecast(feats, mode, day)
    info = feats[(feats["timestamp"].dt.normalize() == day)].iloc[0]
    flags = day_flags(info)
    rain = feats[(feats["timestamp"].dt.normalize() == day) & feats["timestamp"].dt.hour.between(6, 21)]["precipitation"].sum()

    st.subheader(f"Forecast for {day.strftime('%A, %d %B %Y')} · {MODES[mode]}")
    st.caption(f"Model trained on all hours before {day.strftime('%d %b %Y')}; it has not seen this day's data.")

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
    fig.update_layout(xaxis_title=f"Hour of day ({day.strftime('%a %d %b %Y')})", yaxis_title="Passengers", height=420, legend={"orientation": "h"},
                      margin={"t": 10})
    plot(fig)

    st.markdown("**How it works:** the model is retrained on every hour before the selected day and predicts all 24 hours "
                "using only information available a day ahead (lagged demand, calendar, holidays, school breaks, weather). "
                "Full analysis: [reports/results.md](https://github.com/yagmurtncr/istanbul-transit-demand/blob/main/reports/results.md)")
