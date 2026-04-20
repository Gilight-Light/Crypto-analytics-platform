# ADR 001 — Why Apache Iceberg for Bronze/Silver/Gold

**Status**: Accepted
**Date**: 2026-04-19

## Context

We need an open table format for the medallion layers (Bronze / Silver / Gold)
sitting on MinIO (S3-compatible). Candidates:

1. Plain Parquet folders with Hive partitioning
2. Delta Lake
3. Apache Iceberg
4. Apache Hudi

## Decision

Iceberg.

## Consequences

- **Pros**
  - ACID transactions on object storage — micro-batches from Spark Structured
    Streaming commit atomically; no half-written files visible to queries.
  - Schema evolution without rewrites (add/drop/rename column).
  - Hidden partitioning with partition transforms (`days(kafka_timestamp)`,
    `bucket(16, symbol)`) — partition spec can evolve over time.
  - Native `MERGE INTO` for idempotent Silver upserts from Bronze.
  - Time travel (`VERSION AS OF <snapshot_id>`) for ad-hoc debugging.
  - First-class support in Spark, Trino, Flink — future engine changes carry
    fewer migration cost than format-specific Delta.
- **Cons**
  - More moving pieces vs plain Parquet: Hive Metastore + `iceberg-spark-runtime`
    jars + catalog properties per engine.
  - Small-file accretion from frequent streaming commits → compaction
    (`rewrite_data_files`) becomes operational work.

## Alternatives considered

- **Delta Lake** was close second. Ruled out because (a) Trino's Delta connector
  lags Iceberg connector in feature parity, (b) Iceberg's partition spec
  evolution is cleaner for a schema-changing project.
- **Hudi** has great CDC/MERGE story but smaller community and less Trino
  integration in the version bundled with Spark 3.5.
