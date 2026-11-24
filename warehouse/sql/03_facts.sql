-- Facts at their natural grain, keyed to the dimensions.
CREATE OR REPLACE TABLE fct_hourly_ridership AS SELECT * FROM stg_hourly;
CREATE OR REPLACE TABLE fct_line_daily AS SELECT * FROM stg_line_daily;
CREATE OR REPLACE TABLE fct_station_daily AS SELECT * FROM stg_station_daily WHERE station <> '';
CREATE OR REPLACE TABLE fct_district_daily AS SELECT * FROM stg_district_daily;
CREATE OR REPLACE TABLE fct_fare_daily AS SELECT * FROM stg_fare_daily;
CREATE OR REPLACE TABLE fct_line_hour_profile AS SELECT * FROM stg_line_hour_profile;

-- Daily totals per mode, with calendar attributes: the backbone of most marts.
CREATE OR REPLACE TABLE fct_daily_mode AS
SELECT h.date, h.mode_id, SUM(h.passengers) AS passengers, SUM(h.passages) AS passages
FROM fct_hourly_ridership h GROUP BY 1, 2;
