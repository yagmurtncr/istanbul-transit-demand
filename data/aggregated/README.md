# Aggregated İBB data

| File | Rows | Content |
|---|---|---|
| `hourly_by_mode_2022-01_2023-12.csv` | 52,560 | `date, hour, transport_type (road/rail/sea), passengers` |
| `rail_lines_daily_2022-01_2023-12.csv` | 14,891 | `date, line, passengers` for rail lines |
| `hourly_by_mode_2024-01_2024-07.csv` | 15,336 | `date, hour, transport_type (road/rail/sea), passengers` |
| `rail_lines_daily_2024-01_2024-07.csv` | 4,849 | `date, line, passengers` for rail lines (metro, Marmaray, tram, funicular) |
| `weather_istanbul_2022-01_2024-07.csv` | 22,632 | Hourly `temperature_2m`, `precipitation`, `snowfall`, `wind_speed_10m` for central Istanbul (local time) |

**Source:** İBB Açık Veri Portalı — *Saatlik Toplu Ulaşım Veri Seti* (İBB Açık Veri Lisansı). Kaynak: İBB Açık Veri Portalı.

**Weather source:** [Open-Meteo](https://open-meteo.com/) historical weather API (CC BY 4.0). Bundled so the analysis and the in-browser demo run offline.

**How it was built:** the 31 monthly CSVs for January 2022–July 2024 (1.2–1.7 GB and 12–18 million rows each,
about 475 million rows in total) were streamed once and `number_of_passenger` was summed per
(date, hour, transport_type_id) and per (date, rail line). No rows were dropped (0 unparseable rows).

**Why January 2022–July 2024:** 2020–2021 are left out because Covid-19 restrictions changed travel behaviour, and July 2024 is the most recent complete month. The August–October 2024 files
are much smaller than usual and cover only part of each month (October: 18 days), and the
November–December 2024 files are published empty.
