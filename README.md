# Istanbul Public Transport Demand Forecasting

Hourly passenger demand forecasting for Istanbul's public transport network (road, rail and sea), built on open data from the **İBB Açık Veri Portalı** and enriched with weather and the Turkish holiday calendar.

> Status: 🚧 Phase 1 (data pipeline + baseline) in progress. See [TODO.md](TODO.md) for the roadmap.

## Goals
- Forecast next-day hourly demand per transport mode (later: per line / station).
- Quantify, with proper statistical tests, how weather, holidays and special events shift demand.
- Ship it as a production-style system: tested pipeline, experiment tracking, daily automated retraining and a live dashboard.

## Data
| Source | Content | Access |
|---|---|---|
| [İBB Açık Veri — Saatlik Toplu Ulaşım](https://data.ibb.gov.tr/dataset/hourly-public-transport-data-set) | Hourly passenger counts by mode, line and transfer type (monthly CSVs) | CKAN API, İBB open data licence |
| [Open-Meteo Archive API](https://open-meteo.com/) | Hourly temperature, precipitation, snowfall, wind | Free, no key |
| [`holidays`](https://pypi.org/project/holidays/) | Turkish public and religious holidays (incl. eves) | Python package |

Raw data is **not** committed to the repo; the pipeline downloads it into `data/raw/`.

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
pytest                                   # 7 tests: cleaning, leakage, validation, holidays
python scripts/run_phase1.py --months 12 # download -> features -> baseline scores
```

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
_To be added after Phase 2._

## License
Code: MIT. Data: subject to the İBB Open Data Licence and Open-Meteo terms; cite "Kaynak: İBB Açık Veri Portalı".
