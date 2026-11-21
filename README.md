# Istanbul Public Transport Demand Forecasting

Hourly passenger demand forecasting for Istanbul's public transport network (road, rail and sea), built on open data from the **İBB Açık Veri Portalı** and enriched with weather and the Turkish holiday calendar.

> Status: ✅ Phase 1 (data pipeline) · 🚧 Phase 2–3 (statistics & models) running on real data — see **[reports/results.md](reports/results.md)**. Roadmap in [TODO.md](TODO.md).

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
See [reports/results.md](reports/results.md) — regenerated automatically by the `Analysis` GitHub Actions workflow whenever data or model code changes.

## License
Code: MIT. Data: subject to the İBB Open Data Licence and Open-Meteo terms; cite "Kaynak: İBB Açık Veri Portalı".
