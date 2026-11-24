-- Data quality checks: each query returns the rows that violate the rule (an empty result passes).
-- name: no_negative_counts
SELECT * FROM fct_hourly_ridership WHERE passengers < 0 OR passages < 0;
-- name: passengers_not_above_passages
SELECT * FROM fct_hourly_ridership WHERE passengers > passages;
-- name: daily_totals_match_across_facts
WITH h AS (SELECT date, SUM(passengers) p FROM fct_hourly_ridership GROUP BY 1),
     l AS (SELECT date, SUM(passengers) p FROM fct_line_daily GROUP BY 1),
     d AS (SELECT date, SUM(passengers) p FROM fct_district_daily GROUP BY 1),
     f AS (SELECT date, SUM(passengers) p FROM fct_fare_daily GROUP BY 1)
SELECT h.date, h.p, l.p, d.p, f.p FROM h JOIN l USING (date) JOIN d USING (date) JOIN f USING (date)
WHERE h.p <> l.p OR h.p <> d.p OR h.p <> f.p;
-- name: every_fact_day_in_dim_date
SELECT DISTINCT date FROM fct_hourly_ridership WHERE date NOT IN (SELECT date FROM dim_date);
-- name: every_line_in_dim_line
SELECT DISTINCT line_code, mode_id FROM fct_line_daily f
WHERE line_code IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dim_line l WHERE l.line_code = f.line_code AND l.mode_id = f.mode_id);
-- name: every_fare_in_dim_fare
SELECT DISTINCT product_kind, transaction_type, transfer_type FROM fct_fare_daily f
WHERE NOT EXISTS (SELECT 1 FROM dim_fare d WHERE d.product_kind = f.product_kind
                  AND d.transaction_type = f.transaction_type AND d.transfer_type = f.transfer_type);
-- name: mode_shares_sum_to_100
SELECT year, SUM(share_pct) s FROM mart_mode_share GROUP BY 1 HAVING ABS(SUM(share_pct) - 100) > 0.01;
-- name: fare_shares_sum_to_100
SELECT month, SUM(share_pct) s FROM mart_fare_mix_monthly GROUP BY 1 HAVING ABS(SUM(share_pct) - 100) > 0.01;
-- name: partial_months_never_complete
SELECT * FROM dim_month_quality WHERE is_partial AND is_complete;
-- name: hours_in_range
SELECT * FROM fct_hourly_ridership WHERE hour NOT BETWEEN 0 AND 23;
