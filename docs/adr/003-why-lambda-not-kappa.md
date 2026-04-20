# ADR 003 — Why Lambda (not Kappa) architecture

**Status**: Accepted
**Date**: 2026-04-19

## Context

Two architecture patterns for streaming + batch:

- **Lambda**: separate hot path (stream processor) and cold path (batch
  processor over durable event log) with independently optimized sinks.
- **Kappa**: single stream-processing pipeline; all workloads (including
  historical backfills) run through the same code by replaying the event log.

## Decision

Lambda — hot path writes ClickHouse, cold path writes Iceberg medallion, both
fed by the same Kafka topic but via independent Spark Structured Streaming
applications.

## Consequences

- **Pros**
  - Each sink optimized for its read pattern: ClickHouse for sub-second
    dashboards; Iceberg for petabyte-friendly OLAP and ML features.
  - Hot-path outage does not corrupt cold path (different checkpoints, different
    Spark apps). Serving layer degrades, not storage.
  - Backfill semantics are different by design: a late fix to the Silver Spark
    job is re-run as a batch; it does not have to account for real-time
    streaming correctness.
  - Matches what's actually taught in Data Engineering interviews (most real
    fintech stacks are Lambda, not Kappa).
- **Cons**
  - Schema duplication: the trade record is declared in Iceberg DDL, ClickHouse
    DDL, and the Kafka producer — three places to keep in sync.
  - Two streaming jobs' checkpoints to monitor, not one.
  - Small-file problem appears twice (ClickHouse parts + Iceberg manifests);
    both need compaction operators.

## Alternatives considered

- **Kappa** would simplify the story but forces either (a) Flink-based
  streaming that supports batch replay natively, or (b) heroic engineering on
  Spark Structured Streaming to backfill multi-year history at stream speed.
  Complexity/reward did not work out for this stack.
