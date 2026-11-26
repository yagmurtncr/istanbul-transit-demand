-- Dimensions. dim_date is loaded from Python (calendar flags); the others are derived here.
CREATE OR REPLACE TABLE dim_mode AS
SELECT * FROM (VALUES (1, 'road', 'Road (bus, metrobus)'), (2, 'rail', 'Rail (metro, Marmaray, tram, funicular)'),
                      (3, 'sea', 'Sea (ferries)')) AS t(mode_id, mode, mode_label);

CREATE OR REPLACE TABLE dim_month_quality AS
WITH months AS (
    SELECT DISTINCT date_trunc('month', date) AS month FROM stg_hourly
), per_day AS (
    SELECT date_trunc('month', date) AS month, SUM(passengers) / COUNT(DISTINCT date) AS avg_daily,
           COUNT(DISTINCT date) AS days_present
    FROM stg_hourly GROUP BY 1
)
SELECT m.month, p.days_present,
       CAST(date_part('day', last_day(m.month)) AS INTEGER) AS days_in_month,
       p.days_present < date_part('day', last_day(m.month)) OR m.month >= DATE '2024-08-01' AS is_partial,
       m.month BETWEEN DATE '2020-03-01' AND DATE '2021-06-01' AS is_covid_period,
       NOT (p.days_present < date_part('day', last_day(m.month)) OR m.month >= DATE '2024-08-01') AS is_complete
FROM months m JOIN per_day p USING (month);

CREATE OR REPLACE TABLE dim_line AS
SELECT line_code, mode_id, arg_max(route, passengers) AS route, MIN(date) AS first_seen, MAX(date) AS last_seen,
       SUM(passengers) AS lifetime_passengers
FROM stg_line_daily WHERE line_code IS NOT NULL GROUP BY line_code, mode_id;

CREATE OR REPLACE TABLE dim_station AS
SELECT station, mode_id, arg_max(line_code, passengers) AS main_line, SUM(passengers) AS lifetime_passengers
FROM stg_station_daily WHERE station <> '' GROUP BY station, mode_id;

CREATE OR REPLACE TABLE dim_district AS
SELECT DISTINCT district FROM stg_district_daily;

-- product_kind codes as published by İBB, mapped with İBB's own card-type dataset
-- (istanbulkart-yillara-ve-kart-tiplerine-gore-kullanim-verisi): "Indirimli Kart" = student cards,
-- "Indirimli Kart 2" = teacher and 60+ cards. Its 2023 shares (44.3%, 3.2%, full 39.1%, free 13.4%) match ours.
CREATE OR REPLACE TABLE dim_fare AS
SELECT DISTINCT product_kind, transaction_type, transfer_type,
       CASE WHEN product_kind = 'TAM' THEN 'Full fare'
            WHEN product_kind LIKE 'INDIRIMLI1%' THEN 'Student'
            WHEN product_kind LIKE 'INDIRIMLI2%' THEN 'Teacher / 60+'
            WHEN product_kind LIKE 'UCRETSIZ%' THEN 'Free'
            WHEN product_kind = 'PERSONEL' THEN 'Staff'
            ELSE 'Other' END AS card_group,
       CASE WHEN transaction_type ILIKE '%abonman%' THEN 'Subscription'
            WHEN transaction_type ILIKE '%aktarma%' THEN 'Transfer'
            WHEN transaction_type ILIKE '%kontur%' THEN 'Pay per ride'
            WHEN transaction_type ILIKE '%ucretsiz%' THEN 'Free'
            ELSE 'Other' END AS payment_type
FROM stg_fare_daily;
