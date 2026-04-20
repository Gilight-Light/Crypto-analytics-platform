{{
  config(
    materialized='table',
    schema='gold'
  )
}}

WITH ranked AS (
    SELECT
        symbol,
        date_trunc('hour', trade_time)                          AS bucket_hour,
        price,
        quantity,
        quote_quantity,
        trade_time,
        ROW_NUMBER() OVER (
            PARTITION BY symbol, date_trunc('hour', trade_time)
            ORDER BY trade_time ASC
        ) AS rn_first,
        ROW_NUMBER() OVER (
            PARTITION BY symbol, date_trunc('hour', trade_time)
            ORDER BY trade_time DESC
        ) AS rn_last
    FROM {{ ref('stg_trades') }}
)
SELECT
    symbol,
    bucket_hour,
    MAX(CASE WHEN rn_first = 1 THEN price END)   AS open,
    MAX(price)                                    AS high,
    MIN(price)                                    AS low,
    MAX(CASE WHEN rn_last  = 1 THEN price END)    AS close,
    SUM(quantity)                                 AS volume,
    SUM(quote_quantity)                           AS quote_volume,
    COUNT(*)                                      AS trade_count
FROM ranked
GROUP BY symbol, bucket_hour
