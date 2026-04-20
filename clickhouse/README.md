# ClickHouse — real-time serving layer

Hot, aggregated OLAP store for sub-second dashboards. Data lives for 7 days
(TTL); beyond that, query Iceberg Gold via Trino.

## Tables

| Table | Engine | Purpose |
|---|---|---|
| `realtime.trades` | ReplacingMergeTree | Raw trade landing; dedup on `(symbol, trade_id)`. |
| `realtime.trades_1m` | AggregatingMergeTree | 1-minute OHLCV states, fed by `trades_1m_mv`. |
| `realtime.price_latest` | AggregatingMergeTree | Single-row-per-symbol latest price, fed by `price_latest_mv`. |

## Sample queries

Latest prices:
```sql
SELECT symbol, argMaxMerge(price) AS price, max(updated) AS updated
FROM realtime.price_latest
GROUP BY symbol
ORDER BY symbol;
```

OHLCV last 30 minutes:
```sql
SELECT bucket_ts, symbol,
       argMinMerge(open)  AS open,
       max(high)          AS high,
       min(low)           AS low,
       argMaxMerge(close) AS close,
       sum(volume)        AS volume
FROM realtime.trades_1m
WHERE bucket_ts > now() - INTERVAL 30 MINUTE
GROUP BY symbol, bucket_ts
ORDER BY symbol, bucket_ts;
```

## Why AggregatingMergeTree and not SummingMergeTree?

OHLCV needs `argMin(price, time)` and `argMax(price, time)`, which are not
simple sums. `AggregatingMergeTree` stores partial aggregation states that
`-Merge` combinators finalize at query time — the standard pattern for
time-series rollups in ClickHouse.
