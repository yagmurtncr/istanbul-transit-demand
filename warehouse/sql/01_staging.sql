-- Staging: typed views over the aggregated İBB extracts (data/detail/*.csv.gz).
-- transport_type_id: 1 = road (bus, metrobus), 2 = rail, 3 = sea.
CREATE OR REPLACE VIEW stg_hourly AS
SELECT CAST(date AS DATE) AS date, CAST(hour AS INTEGER) AS hour, CAST(transport_type_id AS INTEGER) AS mode_id,
       CAST(passages AS BIGINT) AS passages, CAST(passengers AS BIGINT) AS passengers
FROM read_csv_auto('{DETAIL}/hourly_mode.csv.gz', header = true, all_varchar = true);

CREATE OR REPLACE VIEW stg_line_daily AS
SELECT CAST(date AS DATE) AS date, CAST(transport_type_id AS INTEGER) AS mode_id,
       NULLIF(TRIM(line_code), '') AS line_code, NULLIF(TRIM(route), '') AS route,
       CAST(passages AS BIGINT) AS passages, CAST(passengers AS BIGINT) AS passengers
FROM read_csv_auto('{DETAIL}/line_daily.csv.gz', header = true, all_varchar = true);

CREATE OR REPLACE VIEW stg_station_daily AS
SELECT CAST(date AS DATE) AS date, CAST(transport_type_id AS INTEGER) AS mode_id,
       TRIM(station) AS station, NULLIF(TRIM(line_code), '') AS line_code,
       CAST(passages AS BIGINT) AS passages, CAST(passengers AS BIGINT) AS passengers
FROM read_csv_auto('{DETAIL}/station_daily.csv.gz', header = true, all_varchar = true);

CREATE OR REPLACE VIEW stg_district_daily AS
SELECT CAST(date AS DATE) AS date, CAST(transport_type_id AS INTEGER) AS mode_id,
       COALESCE(NULLIF(TRIM(district), ''), 'UNKNOWN') AS district,
       CAST(passages AS BIGINT) AS passages, CAST(passengers AS BIGINT) AS passengers
FROM read_csv_auto('{DETAIL}/district_daily.csv.gz', header = true, all_varchar = true);

CREATE OR REPLACE VIEW stg_fare_daily AS
SELECT CAST(date AS DATE) AS date, CAST(transport_type_id AS INTEGER) AS mode_id,
       COALESCE(NULLIF(TRIM(product_kind), ''), 'UNKNOWN') AS product_kind,
       COALESCE(NULLIF(TRIM(transaction_type), ''), 'UNKNOWN') AS transaction_type,
       COALESCE(NULLIF(TRIM(transfer_type), ''), 'UNKNOWN') AS transfer_type,
       CAST(passages AS BIGINT) AS passages, CAST(passengers AS BIGINT) AS passengers
FROM read_csv_auto('{DETAIL}/fare_daily.csv.gz', header = true, all_varchar = true);

CREATE OR REPLACE VIEW stg_line_hour_profile AS
SELECT CAST(year AS INTEGER) AS year, CAST(transport_type_id AS INTEGER) AS mode_id,
       NULLIF(TRIM(line_code), '') AS line_code, CAST(hour AS INTEGER) AS hour, CAST(is_weekend AS INTEGER) AS is_weekend,
       CAST(passages AS BIGINT) AS passages, CAST(passengers AS BIGINT) AS passengers
FROM read_csv_auto('{DETAIL}/line_hour_profile.csv.gz', header = true, all_varchar = true);
