{{
  config(
    materialized='view',
    schema='staging'
  )
}}

SELECT
    trade_id,
    symbol,
    price,
    qty                                  AS quantity,
    quote_qty                            AS quote_quantity,
    trade_time,
    event_time,
    CAST(is_buyer_maker AS BOOLEAN)      AS is_buyer_maker
FROM {{ source('silver', 'trades') }}
