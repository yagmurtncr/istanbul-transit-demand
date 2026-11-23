# Istanbul Public Transport Demand Forecasting

[![Hugging Face dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-Hugging%20Face-yellow)](https://huggingface.co/datasets/yagmurtuncer/istanbul-public-transport-hourly-2024) [![Kaggle dataset](https://img.shields.io/badge/Dataset-Kaggle-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com/datasets/nuryamurtuncer/istanbul-public-transport-hourly-passengers-2024)

Hourly passenger demand forecasting for Istanbul's public transport network (road, rail and sea), built on open data from the **İBB Açık Veri Portalı** and enriched with weather and the Turkish holiday calendar.

> Status: ✅ Phase 1 (data pipeline) · 🚧 Phase 2–3 (statistics & models) running on real data — see **[reports/results.md](reports/results.md)**. Roadmap in [TODO.md](TODO.md).

## Goals
- Forecast next-day hourly demand per transport mode (later: per line / station).
- Quantify, with proper statistical tests, how weather, holidays and special events shift demand.
- Ship it as a production-style system: tested pipeline, experiment tracking, daily automated retraining and a live dashboard.

## Data

**Published datasets:** the aggregated data used in this project is available on [Hugging Face](https://huggingface.co/datasets/yagmurtuncer/istanbul-public-transport-hourly-2024) and [Kaggle](https://www.kaggle.com/datasets/nuryamurtuncer/istanbul-public-transport-hourly-passengers-2024) (CC BY 4.0, source: İBB Açık Veri Portalı).
| Source | Content | Access |
|---|---|---|
| [İBB Açık Veri — Saatlik Toplu Ulaşım](https://data.ibb.gov.tr/dataset/hourly-public-transport-data-set) | Hourly passenger counts by mode, line and transfer type (monthly CSVs) | CKAN API, İBB open data licence |
| [Open-Meteo Archive API](https://open-meteo.com/) | Hourly temperature, precipitation, snowfall, wind | Free, no key |
| [`holidays`](https://pypi.org/project/holidays/) | Turkish public and religious holidays (incl. eves) | Python package |

Raw data is **not** committed (each month is ~1.6 GB). Instead, [`data/aggregated/`](data/aggregated/) contains January–July 2024 summed to hourly totals per mode (~120 million raw rows → 15k rows), so the analysis is reproducible in seconds. The full pipeline can still download raw months into `data/raw/`.

## Approach
1. **Pipeline** – download, clean, aggregate to an hourly panel, fill missing hours explicitly.
2. **Features** – calendar (cyclic hour encoding, weekday, holidays, eves), weather, lagged demand (24h / 48h / 168h) and rolling means. All lag features are built so that a day-ahead forecast never sees the future; a unit test enforces this.
3. **Validation** – expanding-window walk-forward splits; metrics: MAE, sMAPE, WAPE.
4. **Models** – seasonal naive → linear models → gradient boosting (XGBoost) with SHAP explanations.
5. **Statistics** – effect of rain and holidays with bootstrap confidence intervals and hypothesis tests.
6. **MLOps** – MLflow tracking, Docker, GitHub Actions CI, scheduled daily retraining on AWS, Streamlit dashboard.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                   # 9 tests: cleaning, leakage, validation, holidays, bootstrap
python scripts/run_analysis.py          # EDA, statistical tests, model comparison -> reports/
python scripts/run_phase1.py --months 6  # optional: re-download raw months from İBB
```

## Interactive dashboard
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
First findings on January–July 2024 (1.43 billion passengers):

- **Public holidays** cut weekday demand by about **27% on rail** and **35% on buses**, while **ferry** use rises by about **77%**.
- **School breaks** lower weekday demand by about **17% on rail** and **21% on buses**; ferries are unaffected.
- **Rain** (≥ 2 mm during the day) reduces demand by about **4% on rail and buses** and **18% on ferries**. This only became visible after separating school breaks from term time: the two effects were masking each other.
- **Gradient boosting with a Poisson loss** (suited to counts) reaches a day-ahead WAPE of about **9.4% (rail)** and **8.1% (road)**, **32–38% lower error** than a same-hour-last-week baseline.

All effects above are statistically significant (bootstrap 95% CI and Mann-Whitney U, p < 0.01). Full tables and figures: [reports/results.md](reports/results.md) — regenerated automatically by the `Analysis` GitHub Actions workflow whenever data or model code changes.

## License
Code: MIT. Data: subject to the İBB Open Data Licence and Open-Meteo terms; cite "Kaynak: İBB Açık Veri Portalı".
