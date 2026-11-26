---
license: mit
library_name: sklearn
tags:
  - tabular-regression
  - time-series-forecasting
  - sklearn
  - skops
  - istanbul
  - public-transport
datasets:
  - yagmurtuncer/istanbul-public-transport-ridership-2020-2024
pipeline_tag: tabular-regression
---

# Istanbul public transport — day-ahead hourly demand models

Three gradient-boosting regressors (scikit-learn `HistGradientBoostingRegressor`, **Poisson loss**), one per
transport mode, that forecast the number of passengers in every hour of the next day for Istanbul's public
transport network. Trained on İBB open data from 2022-01-01 to 2024-07-31
(Covid-19 period excluded), enriched with hourly weather and a Turkish calendar of public and religious
holidays, holiday eves, bridge days, school breaks, Ramadan and election days.

- **Code, analysis and SQL warehouse:** [github.com/yagmurtncr/istanbul-transit-demand](https://github.com/yagmurtncr/istanbul-transit-demand)
- **Try it in your browser:** [Hugging Face Space](https://huggingface.co/spaces/yagmurtuncer/istanbul-transit-demand)

## Performance

Expanding-window walk-forward validation, 4 folds × 14 days at the end of the training period.
WAPE = sum of absolute errors / sum of actual passengers (hourly).

| Mode | File | WAPE | Same hour last week | Improvement |
|---|---|---|---|---|
| Rail (metro, Marmaray, tram, funicular) | `transit_gbm_rail.skops` | 5.6% | 13.8% | 60% |
| Road (bus, metrobus) | `transit_gbm_road.skops` | 4.7% | 13.1% | 64% |
| Sea (ferries) | `transit_gbm_sea.skops` | 8.7% | 19.5% | 56% |

The validation weeks (June–July 2024) are mostly ordinary days. On April–May 2024, which contain Ramazan Bayramı,
23 Nisan, 1 and 19 Mayıs and the local elections, the same models score about 9% (rail), 7% (road) and 14% (ferries):
special days remain the hardest part. Settings were chosen on April–May and confirmed on the held-out June–July weeks.

### Özet (Türkçe)

Model, ertesi günün her saati için yolcu sayısını tahmin ediyor. Saatlik hata raylı sistemde yaklaşık %5,6,
otobüste %4,7, vapurda %8,7. "Geçen hafta aynı saat" yöntemi ise %13–19 hata yapıyor; model hatayı yaklaşık
%60 azaltıyor. Bayram, köprü günü ve seçim gibi özel günlerde hata daha yüksek.

## Inputs

`lag_24`, `lag_48`, `lag_168`, `roll_mean_24`, `roll_mean_168`, `temperature_2m`, `precipitation`, `wind_speed_10m`, `is_holiday`, `is_religious_holiday`, `is_national_holiday`, `is_eve`, `is_half_day`, `is_ramadan`, `is_bridge`, `is_election`, `school_closed`, `is_weekend`, `hour_sin`, `hour_cos`, `hour`, `dow`, `month`

All lag features (`lag_24`, `lag_48`, `lag_168`, rolling means) end at least 24 hours before the forecast hour,
so the model can be run at the end of one day for the whole next day. Build them with
`transit.features.build.build_features` from the GitHub repository.

## Usage

```python
from huggingface_hub import hf_hub_download
from skops.io import load, get_untrusted_types

path = hf_hub_download("yagmurtuncer/istanbul-transit-demand-gbm", "transit_gbm_rail.skops")
model = load(path, trusted=get_untrusted_types(file=path))   # review the listed types before trusting them
# X: one row per hour with the columns listed above, in that order
# passengers = model.predict(X).clip(min=0)
```

## Usage notes

- Trained on data up to July 2024 (the latest complete month published by İBB); demand patterns may drift after that.
- Weather inputs are observed values; in real day-ahead use a weather forecast would replace them, which adds error.
- The calendar flags (school breaks, bridge days) must be extended for dates after 2024.

## Data and license

Source data: İstanbul Büyükşehir Belediyesi Açık Veri Portalı, *Saatlik Toplu Ulaşım Veri Seti* (İBB Open Data
License); weather: Open-Meteo (CC BY 4.0). Model weights: MIT.
