# ADR 002 — Why ClickHouse for the real-time serving layer

**Status**: Accepted
**Date**: 2026-04-19

## Context

The platform needs two serving stores:

1. **Hot**: sub-second queries for Grafana real-time dashboards.
2. **Cold**: full-history OLAP for Superset / ad-hoc analysis.

Cold is covered by Iceberg-on-MinIO queried via Trino (ADR 001). The question
is what powers the hot path.

Candidates:

1. ClickHouse
2. Apache Druid
3. TimescaleDB (Postgres extension)
4. Just Trino over Iceberg

## Decision

ClickHouse, single-node.

## Consequences

- **Pros**
  - Sub-second aggregations on tens of millions of rows without tuning.
  - `ReplacingMergeTree` + `(symbol, trade_id)` sort key absorbs duplicate
    deliveries from Spark checkpoint replay without explicit dedup code.
  - `AggregatingMergeTree` + materialized views give us OHLCV / latest-price
    state that refreshes incrementally as trades land — no query-time GROUP BY
    over raw rows.
  - `LowCardinality(String)` on `symbol` = cheap even with hundreds of symbols.
  - Official Grafana plugin (`grafana-clickhouse-datasource`) makes hooking up
    dashboards trivial.
- **Cons**
  - Operational complexity vs e.g. Postgres — replica/shard topology, keeper
    node, mutations semantics. Acceptable for local dev; real cost in prod.
  - TTL-based data lifecycle (7 days) means you must always query Iceberg Gold
    for longer-range questions.

## Alternatives considered

- **Druid** rules for ingest throughput but heavier to run (6+ services). Over-
  engineered for single-node demo.
- **TimescaleDB**: simpler, but query latency for GROUP BY on millions of rows
  doesn't match ClickHouse, especially without careful continuous aggregates.
- **Trino over Iceberg**: would give "one store to rule them all", but
  sub-second latency on micro-batch data requires a lot of tuning (or adoption
  of the cache+materialized views). Not worth the complexity when ClickHouse
  handles it natively.
