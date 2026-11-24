-- Business marts. Only complete months feed KPIs (dim_month_quality.is_complete).

-- Monthly volume, year-over-year change and recovery index vs Jan-Feb 2020 (pre-pandemic).
CREATE OR REPLACE TABLE mart_monthly_kpis AS
WITH m AS (
    SELECT date_trunc('month', d.date) AS month, d.mode_id, SUM(d.passengers) AS passengers,
           SUM(d.passengers) / COUNT(DISTINCT d.date) AS avg_daily_passengers
    FROM fct_daily_mode d GROUP BY 1, 2
), base AS (
    SELECT mode_id, AVG(avg_daily_passengers) AS base_daily FROM m
    WHERE month IN (DATE '2020-01-01', DATE '2020-02-01') GROUP BY 1
)
SELECT m.month, m.mode_id, m.passengers, m.avg_daily_passengers,
       100.0 * m.avg_daily_passengers / b.base_daily AS recovery_index,
       100.0 * (m.passengers / LAG(m.passengers, 12) OVER (PARTITION BY m.mode_id ORDER BY m.month) - 1) AS yoy_pct,
       q.is_complete, q.is_covid_period
FROM m JOIN base b USING (mode_id) JOIN dim_month_quality q USING (month);

-- Mode share per year (complete months only).
CREATE OR REPLACE TABLE mart_mode_share AS
SELECT year(d.date) AS year, dm.mode_label, SUM(d.passengers) AS passengers,
       100.0 * SUM(d.passengers) / SUM(SUM(d.passengers)) OVER (PARTITION BY year(d.date)) AS share_pct
FROM fct_daily_mode d JOIN dim_mode dm USING (mode_id)
JOIN dim_month_quality q ON q.month = date_trunc('month', d.date) WHERE q.is_complete
GROUP BY 1, 2;

-- Busiest lines and stations of the latest full year (2023).
CREATE OR REPLACE TABLE mart_line_ranking_2023 AS
SELECT l.line_code, l.route, dm.mode_label, SUM(f.passengers) AS passengers,
       SUM(f.passengers) / 365.0 AS avg_daily_passengers,
       RANK() OVER (ORDER BY SUM(f.passengers) DESC) AS rank
FROM fct_line_daily f JOIN dim_line l USING (line_code, mode_id) JOIN dim_mode dm USING (mode_id)
WHERE year(f.date) = 2023 GROUP BY 1, 2, 3;

CREATE OR REPLACE TABLE mart_station_ranking_2023 AS
SELECT f.station, dm.mode_label, s.main_line, SUM(f.passengers) AS passengers,
       RANK() OVER (ORDER BY SUM(f.passengers) DESC) AS rank
FROM fct_station_daily f JOIN dim_station s USING (station, mode_id) JOIN dim_mode dm USING (mode_id)
WHERE year(f.date) = 2023 GROUP BY 1, 2, 3;

-- District of the boarding. Only reliable for rail and ferries (fixed stations and piers): for road,
-- 55% of 2023 boardings carry the district BAKIRKOY, a recording artefact rather than a location.
CREATE OR REPLACE TABLE mart_district_2023 AS
SELECT district, SUM(passengers) AS passengers, 100.0 * SUM(passengers) / SUM(SUM(passengers)) OVER () AS share_pct,
       100.0 * SUM(passengers) FILTER (WHERE mode_id = 2) / SUM(passengers) AS rail_share_pct
FROM fct_district_daily WHERE year(date) = 2023 AND mode_id IN (2, 3) AND district <> 'UNKNOWN' GROUP BY 1;

-- Fare mix per month: card groups and payment types (share of passengers).
CREATE OR REPLACE TABLE mart_fare_mix_monthly AS
SELECT date_trunc('month', f.date) AS month, df.card_group, df.payment_type, SUM(f.passengers) AS passengers,
       100.0 * SUM(f.passengers) / SUM(SUM(f.passengers)) OVER (PARTITION BY date_trunc('month', f.date)) AS share_pct
FROM fct_fare_daily f JOIN dim_fare df USING (product_kind, transaction_type, transfer_type)
GROUP BY 1, 2, 3;

-- Capacity: average weekday passengers in each line's busiest hour (2023) and how peaky the line is.
CREATE OR REPLACE TABLE mart_peak_load_2023 AS
WITH weekdays AS (SELECT COUNT(*) AS n FROM dim_date WHERE year(date) = 2023 AND day_of_week < 5),
p AS (
    SELECT line_code, mode_id, hour, passengers / (SELECT n FROM weekdays) AS avg_weekday_passengers
    FROM fct_line_hour_profile WHERE year = 2023 AND is_weekend = 0
)
SELECT p.line_code, l.route, dm.mode_label,
       arg_max(p.hour, p.avg_weekday_passengers) AS peak_hour,
       MAX(p.avg_weekday_passengers) AS peak_hour_passengers,
       SUM(p.avg_weekday_passengers) AS weekday_passengers,
       100.0 * MAX(p.avg_weekday_passengers) / NULLIF(SUM(p.avg_weekday_passengers), 0) AS peak_share_pct
FROM p JOIN dim_line l USING (line_code, mode_id) JOIN dim_mode dm USING (mode_id)
GROUP BY 1, 2, 3;

-- Holidays, bridge days and school breaks per line: demand vs the same weekday in ordinary weeks of the same month.
CREATE OR REPLACE TABLE mart_line_daytype_effect AS
WITH d AS (
    SELECT f.line_code, f.mode_id, f.date, f.passengers, c.day_of_week, date_trunc('month', f.date) AS month,
           CASE WHEN c.is_religious_holiday = 1 THEN 'Religious holiday'
                WHEN c.is_bridge = 1 THEN 'Bridge day'
                WHEN c.is_national_holiday = 1 THEN 'National holiday'
                WHEN c.school_closed = 1 AND c.day_of_week < 5 THEN 'School break weekday'
                WHEN c.is_eve = 0 AND c.is_half_day = 0 AND c.day_of_week < 5 THEN 'Ordinary weekday'
           END AS day_type
    FROM fct_line_daily f JOIN dim_date c USING (date)
    JOIN dim_month_quality q ON q.month = date_trunc('month', f.date)
    WHERE q.is_complete AND NOT q.is_covid_period AND f.line_code IS NOT NULL
), ordinary AS (
    SELECT line_code, mode_id, AVG(passengers) AS ordinary_weekday FROM d
    WHERE day_type = 'Ordinary weekday' AND day_of_week < 5 GROUP BY 1, 2
)
SELECT d.line_code, l.route, dm.mode_label, d.day_type, COUNT(*) AS days, AVG(d.passengers) AS avg_passengers,
       o.ordinary_weekday, 100.0 * (AVG(d.passengers) / o.ordinary_weekday - 1) AS change_pct
FROM d JOIN ordinary o USING (line_code, mode_id) JOIN dim_line l USING (line_code, mode_id) JOIN dim_mode dm USING (mode_id)
WHERE d.day_type IN ('Religious holiday', 'Bridge day', 'National holiday', 'School break weekday')
  AND d.day_of_week < 5 AND o.ordinary_weekday >= 2000
GROUP BY 1, 2, 3, 4, o.ordinary_weekday;

-- Transfer rate per mode and year.
CREATE OR REPLACE TABLE mart_transfer_rate AS
SELECT year(date) AS year, dm.mode_label,
       100.0 * SUM(passengers) FILTER (WHERE transfer_type = 'Aktarma') / SUM(passengers) AS transfer_pct
FROM fct_fare_daily JOIN dim_mode dm USING (mode_id) GROUP BY 1, 2;
