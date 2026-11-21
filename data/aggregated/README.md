# Aggregated İBB data

| File | Rows | Content |
|---|---|---|
| `hourly_by_mode_2024-01_2024-07.csv` | 15,336 | `date, hour, transport_type (road/rail/sea), passengers` |
| `rail_lines_daily_2024-01_2024-07.csv` | 4,849 | `date, line, passengers` for rail lines (metro, Marmaray, tram, funicular) |

**Source:** İBB Açık Veri Portalı — *Saatlik Toplu Ulaşım Veri Seti* (İBB Açık Veri Lisansı). Kaynak: İBB Açık Veri Portalı.

**How it was built:** the seven monthly CSVs for January–July 2024 (~1.6 GB and ~17 million rows each,
about 120 million rows in total) were streamed once and `number_of_passenger` was summed per
(date, hour, transport_type_id) and per (date, rail line). No rows were dropped (0 unparseable rows).

**Why January–July 2024:** these are the most recent complete months. The August–October 2024 files
are much smaller than usual and cover only part of each month (October: 18 days), and the
November–December 2024 files are published empty.
