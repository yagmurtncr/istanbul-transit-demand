# Roadmap — Istanbul Transit Demand

## Done
- [x] Project skeleton, tests, CI (ruff + pytest), look-ahead leakage test
- [x] İBB CKAN downloader; all 58 monthly files (Jan 2020 – Oct 2024, 701.7M rows) streamed and aggregated
- [x] Hourly panel 2022–2024 plus line, station, district and fare tables 2020–2024 (`data/aggregated/`, `data/detail/`)
- [x] Calendar: public and religious holidays, eves, bridge days, school breaks (MEB 2021–22 to 2023–24), Ramadan, elections
- [x] Weather (Open-Meteo), including a day-ahead forecast stress test
- [x] Statistics: bootstrap CIs, Mann-Whitney U, multivariate regression of calendar and weather effects (`reports/factors.md`)
- [x] Models: seasonal naive, ridge, XGBoost, gradient boosting with Poisson loss; walk-forward validation; SHAP
- [x] DuckDB star-schema warehouse with 10 data-quality checks and business marts (`warehouse/`)
- [x] Business report (`reports/business_insights.md`) and Tableau Public dashboard
- [x] Fare codes mapped with İBB's card-type dataset (INDIRIMLI1 = student, INDIRIMLI2 = teacher / 60+)
- [x] MLflow tracking, Docker image on GHCR, automatic retraining and reports in GitHub Actions
- [x] Live demo (Hugging Face Space), published model, datasets on Hugging Face and Kaggle, Medium article

## Ideas for later
- [ ] Event study plots around each bayram
- [ ] Permutation tests with Benjamini-Hochberg correction
- [ ] Free-transport days as a separate feature
- [ ] Error analysis by hour and day type; a rule for night hours when lines are closed
- [ ] University calendar in addition to the MEB school calendar
- [ ] Line-level forecasts
- [ ] Cloud deployment (for example AWS) with scheduled retraining and simple monitoring
- [ ] Extend the data when İBB publishes months after July 2024
