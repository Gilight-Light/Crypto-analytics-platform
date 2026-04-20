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

| DAG | Schedule | What it does |
|---|---|---|
| `binance_klines_backfill` | `@daily` | Pull last-24h 1h OHLCV from Binance REST per symbol → `s3://bronze/klines_1h/`. |
| `coingecko_snapshot` | `@hourly` | Pull top-250 coins by market cap → `s3://bronze/coingecko_top250/`. |

Both sources are public / keyless-free-tier.

## Access

UI: http://localhost:8088 (login `admin` / `admin`)

## Manual trigger

```bash
docker exec airflow-scheduler airflow dags trigger binance_klines_backfill
docker exec airflow-scheduler airflow dags trigger coingecko_snapshot
```
