# Airflow

Batch ingestion + orchestration for the cold path.

## Services (profile `batch`)

| Service | Purpose |
|---|---|
| `airflow-init` | One-shot `db migrate` + create admin user. Idempotent. |
| `airflow-scheduler` | Parses DAGs, schedules tasks (LocalExecutor). |
| `airflow-webserver` | UI at http://localhost:8088. |

Backend DB: shared Postgres, database `airflow` (created by `postgres/init.sql`).
Executor: **LocalExecutor** — single machine, no Celery/Redis.

## DAGs

### Ingestion (public / keyless free-tier APIs)

| DAG | Schedule | What it does |
|---|---|---|
| `binance_klines_backfill` | `@daily` | Pull last-24h 1h OHLCV from Binance REST per symbol → `s3://bronze/klines_1h/`. |
| `coingecko_snapshot` | `@hourly` | Pull top-250 coins by market cap → `s3://bronze/coingecko_top250/`. |

### Spark jobs (submitted via `SparkSubmitOperator`)

| DAG | Schedule | What it does |
|---|---|---|
| `spark_trades_to_clickhouse` | manual | Kafka → ClickHouse streaming. Long-running task; trigger once, leave running. |
| `spark_trades_to_iceberg` | manual | Kafka → Iceberg bronze streaming. Long-running; exactly-once via Iceberg commits. |
| `spark_bronze_to_silver_trades` | `@hourly` | Dedupe `iceberg.bronze.trades` → `iceberg.silver.trades`. |

Spark connection: `spark_default = spark://spark-master:7077` (set via `AIRFLOW_CONN_SPARK_DEFAULT`).
The Airflow image is a multi-stage build that copies `/opt/spark` (with Iceberg / Kafka / ClickHouse-JDBC / S3A jars baked in) from `crypto-platform/spark:3.5.3`, so the driver runs in client mode inside the Airflow scheduler container and has every jar it needs.

## Access

UI: http://localhost:8088 (login `admin` / `admin`)

## Manual trigger

```bash
docker exec airflow-scheduler airflow dags trigger binance_klines_backfill
docker exec airflow-scheduler airflow dags trigger coingecko_snapshot
docker exec airflow-scheduler airflow dags trigger spark_trades_to_clickhouse
docker exec airflow-scheduler airflow dags trigger spark_trades_to_iceberg
docker exec airflow-scheduler airflow dags trigger spark_bronze_to_silver_trades
```
