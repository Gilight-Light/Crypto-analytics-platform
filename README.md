# Real-time Crypto Analytics Platform

End-to-end real-time + batch data platform for crypto market data. Binance
WebSocket trades flow through Kafka and Spark Structured Streaming into both
ClickHouse (sub-second dashboards) and an Iceberg medallion warehouse on MinIO
(Bronze → Silver → Gold). Airflow pulls hourly / daily batches from CoinGecko
and Binance REST. Trino serves Iceberg to Superset; Grafana serves ClickHouse.
All local, orchestrated via Docker Compose.

## Architecture

```
Binance WS  ─┐
             ├─► Kafka ─► Spark Streaming ─┬─► ClickHouse  (real-time, 7d TTL)
             │                             └─► Iceberg Bronze (MinIO)
CoinGecko /  │
Binance REST ├─► Airflow ─► Spark Batch ─► Iceberg (Bronze → Silver → Gold)
─────────────┘                                         │
                                                       └─► dbt ─► Trino ─► Superset
```

## Stack

| Layer | Tool |
|---|---|
| Message bus | Apache Kafka (KRaft) |
| Object storage | MinIO (S3-compatible) |
| Table format | Apache Iceberg |
| Metastore | Hive Metastore (standalone) |
| Stream + batch | Apache Spark 3.5 |
| SQL transform | dbt-core + dbt-trino |
| OLAP (hot) | ClickHouse |
| Query engine | Trino |
| Orchestration | Apache Airflow |
| BI | Apache Superset |
| Real-time dashboard | Grafana |
| Metadata RDBMS | Postgres |

## Quick start

```bash
make env                                          # create .env from template
make build PROFILES="streaming batch serving"     # build custom images
make up    PROFILES="streaming batch serving"     # bring up the stack
make healthcheck                                  # probe each service
```

Smaller subsets when RAM is tight:

```bash
make up                             # foundation only (~1.6GB)
make up PROFILES="streaming"        # + real-time path (~5GB)
make up PROFILES="batch"            # + Airflow (~7GB)
make up PROFILES="serving"          # + Trino + Superset (~9GB)
```

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| MinIO console | http://localhost:9001 | `minioadmin` / `minioadmin123` |
| MinIO S3 API | http://localhost:9000 | |
| Kafka (host) | `localhost:29092` | |
| Postgres | `localhost:15432` | `platform` / `platform_pw` |
| Hive Metastore | `thrift://localhost:9083` | |
| ClickHouse | http://localhost:8123 | `default` / `clickhouse_pw` |
| Spark Master UI | http://localhost:8080 | |
| Spark Worker UI | http://localhost:8081 | |
| Grafana | http://localhost:3000 | `admin` / `admin` |
| Airflow | http://localhost:8088 | `admin` / `admin` |
| Trino | http://localhost:8082 | no-auth (dev) |
| Superset | http://localhost:8089 | `admin` / `admin` |

## Repository layout

```
crypto-analytics-platform/
├── docker-compose.yml
├── Makefile
├── producers/binance_ws_producer/   # WebSocket → Kafka
├── spark/                            # Spark image with bundled connector jars
├── spark_jobs/
│   ├── streaming/                    # Kafka → Iceberg + Kafka → ClickHouse
│   └── batch/                        # Bronze → Silver
├── airflow/dags/                     # Binance klines + CoinGecko DAGs
├── dbt/models/                       # staging + marts (iceberg.gold.*)
├── clickhouse/init.sql               # hot-path DDL + MVs
├── hive-metastore/                   # Iceberg catalog
├── trino/                            # query engine config
├── superset/                         # BI image + config
├── grafana/                          # provisioned datasources + dashboards
├── postgres/init.sql                 # shared metadata DBs
├── docs/adr/                         # architecture decision records
└── scripts/                          # healthcheck + smoke_test
```

## License

MIT
