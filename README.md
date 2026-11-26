# Istanbul Public Transport: Analytics & Demand Forecasting

[![Live demo](https://img.shields.io/badge/%E2%96%B6%20Live%20demo-Hugging%20Face%20Space-ff9d00)](https://huggingface.co/spaces/yagmurtuncer/istanbul-transit-demand) [![Hugging Face model](https://img.shields.io/badge/%F0%9F%A4%97%20Model-Hugging%20Face-yellow)](https://huggingface.co/yagmurtuncer/istanbul-transit-demand-gbm) [![Hugging Face dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-Hugging%20Face-yellow)](https://huggingface.co/datasets/yagmurtuncer/istanbul-public-transport-ridership-2020-2024) [![Kaggle dataset](https://img.shields.io/badge/Dataset-Kaggle-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com/datasets/nuryamurtuncer/istanbul-public-transport-hourly-passengers-2024) [![Tableau Public](https://img.shields.io/badge/Dashboard-Tableau%20Public-E97627?logo=tableau&logoColor=white)](https://public.tableau.com/app/profile/ya.mur.tuncer/viz/IstanbulPublicTransportAnalytics2020-2024/Recoveryindex)

An end-to-end analytics and machine-learning project on **701.7 million rows** of Istanbul public transport data (January 2020 – October 2024, İBB Açık Veri Portalı): a **SQL star-schema warehouse** (DuckDB) with business marts, **statistical analysis** of what moves demand, and **day-ahead hourly forecasts** you can try in a live demo.

## Business questions answered

| Question | Answer (from the data) | Where |
|---|---|---|
| How big is the network and has it recovered from the pandemic? | 2.45 billion boardings (2.37 billion passengers) in 2023, passengers +4% vs 2022. Rail is at **123%** of its pre-pandemic level, buses still at **94%**: demand has shifted to rail. | [business insights](reports/business_insights.md) |
| Where is capacity tightest? | 10 lines carry half of all boardings. Metrobüs 34 moves **~73,000 passengers in its 18:00 hour** on an average weekday; Marmaray ~60,000. | [business insights](reports/business_insights.md) |
| Who pays what? | 45% student cards, 37% full fare, 14% free, 3% teacher / 60+ (2023). The student share follows the school calendar: about 42% in summer, 51% in October–December, and it rises every year. | [business insights](reports/business_insights.md) |
| How should service change on special days? | Bridge days cut the median line by **33%**, religious holidays by **26%**, while Bosphorus ferries rise by up to **+161%**. | [business insights](reports/business_insights.md) |
| What drives demand, all else equal? | Bridge days −31%, elections −30%, school breaks −8 to −11%, every 10 mm of rain −6% (ferries −22%). Single-day national holidays such as 23 Nisan and 19 Mayıs barely move rail (−2%, not significant) but lift ferries by 39%. | [factors](reports/factors.md) |
| Can we forecast tomorrow, hour by hour? | Yes: the published models reach 5.6% (rail), 5.2% (road) and 8.7% (ferries) hourly error, about 60% better than "same hour last week"; for Ramazan Bayramı 2024 the error fell from 40–44% to 11–15% once 2.5 years of history were used. | [model](https://huggingface.co/yagmurtuncer/istanbul-transit-demand-gbm), [results](reports/results.md), [live demo](https://huggingface.co/spaces/yagmurtuncer/istanbul-transit-demand) |

## SQL warehouse (DuckDB)

`warehouse/sql/` builds a star schema in four layers: **staging** views over the extracts → **dimensions** (`dim_date` with holidays, school breaks, bridge days, Ramadan and elections; `dim_mode`, `dim_line`, `dim_station`, `dim_district`, `dim_fare`, `dim_month_quality`) → **facts** (hourly, line, station, district and fare grain) → **business marts** (monthly KPIs and recovery index, line and station rankings, peak-hour load, fare mix, transfer rate, special-day effect per line). Ten data-quality checks run on every build (for example: hourly, line, district and fare totals must match for every day; partially published months can never count as complete).

```bash
python warehouse/build.py          # ~1 minute: builds data/warehouse.duckdb, runs the checks, exports the marts
python scripts/business_report.py  # writes reports/business_insights.md
```

**Tableau Public dashboard:** the marts are exported to [`tableau/istanbul_transit_tableau.xlsx`](tableau/) on every build and visualised in an [interactive Tableau dashboard](https://public.tableau.com/app/profile/ya.mur.tuncer/viz/IstanbulPublicTransportAnalytics2020-2024/Recoveryindex) (recovery index, peak hours by line, fare mix, holiday effect per line).

Data caveats found while building it, and how they are handled: August–October 2024 are only partially published (flagged, excluded from KPIs); 55% of bus boardings are recorded under the district Bakırköy (district analysis uses rail and ferries only); the fare codes are not documented in the ridership dataset, so they were mapped with İBB’s own card-type dataset (discounted code 1 = student, code 2 = teacher and 60+; its 2023 shares match ours within one point).

> Status: ✅ data pipeline · ✅ SQL warehouse · ✅ statistics & forecasting · ✅ live demo. Roadmap in [TODO.md](TODO.md).

## Goals
- Forecast next-day hourly demand per transport mode (later: per line / station).
- Quantify, with proper statistical tests, how weather, holidays and special events shift demand.
- Ship it as a production-style system: tested pipeline, experiment tracking, daily automated retraining and a live dashboard.

## Data

**Published datasets:** the aggregated data used in this project is available on [Hugging Face](https://huggingface.co/datasets/yagmurtuncer/istanbul-public-transport-ridership-2020-2024) and [Kaggle](https://www.kaggle.com/datasets/nuryamurtuncer/istanbul-public-transport-hourly-passengers-2024) (CC BY 4.0, source: İBB Açık Veri Portalı).
| Source | Content | Access |
|---|---|---|
| [İBB Açık Veri — Saatlik Toplu Ulaşım](https://data.ibb.gov.tr/dataset/hourly-public-transport-data-set) | Hourly passenger counts by mode, line and transfer type (monthly CSVs) | CKAN API, İBB open data licence |
| [Open-Meteo Archive API](https://open-meteo.com/) | Hourly temperature, precipitation, snowfall, wind | Free, no key |
| [`holidays`](https://pypi.org/project/holidays/) | Turkish public and religious holidays (incl. eves) | Python package |

Raw data is **not** committed (each month is ~1.6 GB). Instead, [`data/aggregated/`](data/aggregated/) holds January 2022 – July 2024 summed to hourly totals per mode, and [`data/detail/`](data/detail/) holds daily line, station, district and fare tables for January 2020 – October 2024 (701.7 million raw rows in total), so the analysis is reproducible in seconds. The full pipeline can still download raw months into `data/raw/`.

## Approach
1. **Pipeline** – download, clean, aggregate to an hourly panel, fill missing hours explicitly.
2. **Features** – calendar (cyclic hour encoding, weekday, holidays, eves), weather, lagged demand (24h / 48h / 168h) and rolling means. All lag features are built so that a day-ahead forecast never sees the future; a unit test enforces this.
3. **Validation** – expanding-window walk-forward splits; metrics: MAE, sMAPE, WAPE.
4. **Models** – seasonal naive → ridge → gradient boosting (scikit-learn with a Poisson loss, and XGBoost), explained with SHAP.
5. **Statistics** – bootstrap confidence intervals and Mann-Whitney tests, plus a multivariate regression that separates holidays, bridge days, school breaks, Ramadan, elections and weather.
6. **MLOps** – MLflow tracking, a Docker image on GitHub Container Registry, GitHub Actions for tests, reports, the SQL warehouse and retraining, and a Streamlit dashboard.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                   # 9 tests: cleaning, leakage, validation, holidays, bootstrap
python scripts/run_analysis.py          # EDA, statistical tests, model comparison -> reports/
python scripts/run_phase1.py --months 6  # optional: re-download raw months from İBB
```

## MLOps and explainability

- **Experiment tracking:** every training run is logged to MLflow (parameters, metrics and model files); the Train model workflow uploads the MLflow store as a build artifact.
- **Container:** `docker run -p 8501:8501 ghcr.io/yagmurtncr/istanbul-transit-demand:latest` starts the dashboard at http://localhost:8501. The image is built, smoke-tested and published to GitHub Container Registry by the Docker image workflow.
- **Automation:** GitHub Actions runs the tests, rebuilds the warehouse and every report, retrains the models and refreshes the dashboard screenshots whenever data or code change.
- **Explainability and a real day-ahead test:** [reports/explainability.md](reports/explainability.md) has SHAP plots for each model, and the same models tested with the weather forecast issued the day before instead of the observed weather: the error rises by less than half a point (rail 5.65% to 5.70%, road 4.76% to 4.82%, ferries 9.03% to 9.46%).

## Interactive dashboard

**▶️ Try it live (no install, runs in your browser): [huggingface.co/spaces/yagmurtuncer/istanbul-transit-demand](https://huggingface.co/spaces/yagmurtuncer/istanbul-transit-demand)**

| A normal day: rail, 31 July 2024 | A holiday: buses, 17 June 2024 (Kurban Bayramı) |
|---|---|
| ![Rail forecast](reports/figures/dashboard/rail_2024-07-31.png) | ![Holiday forecast](reports/figures/dashboard/road_holiday_2024-06-17.png) |

On a normal day the hourly error is around 1–2%. On the first day of Kurban Bayramı the model still over-forecasts buses by about 21%, yet it is far closer than the same-hour-last-week baseline (24% vs 70% hourly error): holidays are rare in the training data, which is the main room for improvement. Screenshots are regenerated by the Analysis workflow.

Run it locally:
```bash
pip install -e ".[app]"
streamlit run app/streamlit_app.py
```
Pick a mode and a day: the model is retrained on all data before that day and forecasts its 24 hours, shown against the actual counts and the same-hour-last-week baseline, together with the day type (holiday, school break, weekend) and rainfall.

## Project structure
```
src/transit/
  data/      ibb.py (download), clean.py (hourly panel), external.py (weather, holidays)
  features/  build.py (calendar, lag and rolling features)
  models/    baseline.py (walk-forward CV, metrics, seasonal naive)
scripts/     run_phase1.py
tests/       unit tests incl. a look-ahead leakage test
notebooks/   EDA and analysis
```

## Results
Findings on January 2022 – July 2024 (943 days, 6.07 billion passengers), working days:

- **Public holidays** cut weekday demand by about **21% on rail** and **29% on buses**, while **ferry** use rises by about **90%**.
- **School breaks** lower weekday demand by about **15% on rail** and **18% on buses**; ferries rise slightly (+5%).
- **Rain** (≥ 2 mm during the day) reduces demand by about **5% on rail**, **6% on buses** and **22% on ferries**. This only became visible after separating school breaks from term time: the two effects were masking each other.
- **Gradient boosting with a Poisson loss** reaches a day-ahead hourly WAPE of **5.6% (rail)**, **4.7% (road, tuned)** and **8.7% (ferries)**, about **60% lower error** than a same-hour-last-week baseline; using the weather forecast issued the day before changes it by less than half a point.
- A multivariate regression that holds weekday, month, year and weather fixed separates the calendar further (bridge days −31%, elections −30%, single-day national holidays barely affect rail): [reports/factors.md](reports/factors.md).

All effects above are statistically significant (bootstrap 95% CI and Mann-Whitney U, p < 0.01). Full tables and figures: [reports/results.md](reports/results.md) — regenerated automatically by the `Analysis` GitHub Actions workflow whenever data or model code changes.

## License
Code: MIT. Data: subject to the İBB Open Data Licence and Open-Meteo terms; cite "Kaynak: İBB Açık Veri Portalı".
