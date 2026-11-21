# Results (İBB data, January–July 2024)

Data: 15,336 hourly rows, 213 days, 1.43 billion recorded passengers (rail 625 M, road 769 M, sea 38 M).
Weather: Open-Meteo hourly archive for central Istanbul. Holidays: `holidays` package (incl. eves).

## Demand patterns

![Hourly profile](figures/hourly_profile.png)

![Daily series](figures/daily_series.png)

## Statistical tests

Working days only (Mon–Fri, excluding holiday eves). Rainy day = at least 2 mm of rain between 06:00 and 22:00; dry day = under 0.2 mm. Percentile bootstrap (5,000 resamples) and two-sided Mann-Whitney U test.

| Mode | Rain effect | Public-holiday effect |
|---|---|---|
| rail | -1.8% (95% CI -5.4% to +1.9%, p=0.139, not significant; n=31 vs 84) | -23.5% (95% CI -30.7% to -15.4%, p=0.000, significant; n=10 vs 143) |
| road | -1.9% (95% CI -5.9% to +2.3%, p=0.054, not significant; n=31 vs 84) | -30.8% (95% CI -35.5% to -25.0%, p=0.000, significant; n=10 vs 143) |
| sea | -14.8% (95% CI -20.8% to -9.0%, p=0.000, significant; n=31 vs 84) | +75.8% (95% CI +40.4% to +106.3%, p=0.000, significant; n=10 vs 143) |

![Effects](figures/effects.png)

## Forecasting (hourly, day-ahead features)

Expanding-window walk-forward validation, 4 folds × 14 days. All lag features end at least 24 h before the forecast hour (enforced by a unit test).

### Rail (metro, Marmaray, tram)

| model                      |     MAE |   sMAPE |   WAPE |   WAPE vs naive |
|:---------------------------|--------:|--------:|-------:|----------------:|
| XGBoost                    | 11025   |   32.1  |  10.04 |          -27.26 |
| Gradient boosting          | 12328   |   36.06 |  11.23 |          -18.61 |
| Ridge                      | 14715.8 |   47.5  |  13.47 |           -2.42 |
| Seasonal naive (last week) | 15109.4 |   23.39 |  13.8  |            0    |

### Road (bus, metrobus)

| model                      |     MAE |   sMAPE |   WAPE |   WAPE vs naive |
|:---------------------------|--------:|--------:|-------:|----------------:|
| XGBoost                    | 11933   |   17.67 |   9.15 |          -30.11 |
| Gradient boosting          | 13114.5 |   19.65 |  10.09 |          -22.9  |
| Ridge                      | 16913   |   44.06 |  13    |           -0.69 |
| Seasonal naive (last week) | 17051.2 |   13.32 |  13.09 |            0    |

![Forecast](figures/forecast_rail.png)

![Importance](figures/importance_rail.png)
