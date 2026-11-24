# Detailed İBB extracts (input of the SQL warehouse)

Built by streaming all 58 monthly files of *Saatlik Toplu Ulaşım Veri Seti* (January 2020 – October 2024)
once and summing `number_of_passage` (validated boardings, one per card tap) and `number_of_passenger`.
Every file is gzip-compressed CSV; `transport_type_id`: 1 = road, 2 = rail, 3 = sea.

| File | Grain |
|---|---|
| `hourly_mode.csv.gz` | date × hour × mode |
| `line_daily.csv.gz` | date × mode × line code × route |
| `station_daily.csv.gz` | date × mode × station × line code (stations are recorded for rail and metrobus) |
| `district_daily.csv.gz` | date × mode × district (where the boarding happened) |
| `fare_daily.csv.gz` | date × mode × product kind × transaction type × transfer type |
| `line_hour_profile.csv.gz` | year × mode × line code × hour × weekday/weekend |

August–October 2024 are published only partially by İBB (rows are missing); `dim_month_quality` flags them,
and March 2020 – June 2021 as the Covid-19 period. Source: İBB Açık Veri Portalı (İBB Open Data License).
