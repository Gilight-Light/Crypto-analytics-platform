CREATE DATABASE IF NOT EXISTS realtime;

CREATE TABLE IF NOT EXISTS realtime.trades
(
    trade_id         UInt64,
    symbol           LowCardinality(String),
    price            Float64,
    qty              Float64,
    quote_qty        Float64,
    trade_time       DateTime64(3),
    event_time       DateTime64(3),
    is_buyer_maker   UInt8,
    ingested_at      DateTime64(3),
    kafka_partition  UInt32,
    kafka_offset     UInt64,
    kafka_timestamp  DateTime64(3)
)
ENGINE = ReplacingMergeTree(kafka_timestamp)
PARTITION BY toDate(trade_time)
ORDER BY (symbol, trade_id)
TTL toDateTime(trade_time) + INTERVAL 7 DAY
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS realtime.trades_1m
(
    bucket_ts     DateTime,
    symbol        LowCardinality(String),
    open          AggregateFunction(argMin, Float64, DateTime64(3)),
    high          SimpleAggregateFunction(max, Float64),
    low           SimpleAggregateFunction(min, Float64),
    close         AggregateFunction(argMax, Float64, DateTime64(3)),
    volume        SimpleAggregateFunction(sum, Float64),
    quote_volume  SimpleAggregateFunction(sum, Float64),
    trade_count   SimpleAggregateFunction(sum, UInt64)
)
ENGINE = AggregatingMergeTree()
PARTITION BY toDate(bucket_ts)
ORDER BY (symbol, bucket_ts)
TTL bucket_ts + INTERVAL 7 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS realtime.trades_1m_mv TO realtime.trades_1m AS
SELECT
    toStartOfMinute(trade_time)             AS bucket_ts,
    symbol,
    argMinState(price, trade_time)          AS open,
    max(price)                              AS high,
    min(price)                              AS low,
    argMaxState(price, trade_time)          AS close,
    sum(qty)                                AS volume,
    sum(quote_qty)                          AS quote_volume,
    toUInt64(count())                       AS trade_count
FROM realtime.trades
GROUP BY symbol, bucket_ts;

CREATE TABLE IF NOT EXISTS realtime.price_latest
(
    symbol   LowCardinality(String),
    price    AggregateFunction(argMax, Float64, DateTime64(3)),
    updated  SimpleAggregateFunction(max, DateTime64(3))
)
ENGINE = AggregatingMergeTree()
ORDER BY symbol;

CREATE MATERIALIZED VIEW IF NOT EXISTS realtime.price_latest_mv TO realtime.price_latest AS
SELECT
    symbol,
    argMaxState(price, trade_time)  AS price,
    max(trade_time)                 AS updated
FROM realtime.trades
GROUP BY symbol;
