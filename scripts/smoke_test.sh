#!/usr/bin/env bash
# End-to-end smoke test. Assumes full stack is up: make up PROFILES="streaming batch serving"
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

G=$'\e[32m'; R=$'\e[31m'; C=$'\e[36m'; B=$'\e[1m'; DIM=$'\e[2m'; N=$'\e[0m'

hdr() { printf "\n${B}${C}%s${N}\n${DIM}%s${N}\n" "$1" "────────────────────────────────────────────────"; }

hdr "1. Kafka — raw_trades offset by partition"
docker exec kafka /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic raw_trades

hdr "2. Iceberg Bronze — rows per symbol (via Spark)"
docker exec spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.cores.max=2 \
  /opt/spark_jobs/query_bronze.py 2>&1 \
  | grep -vE "^[0-9]{2}/[0-9]{2}/[0-9]{2} [0-9:]+ (INFO|WARN)|SLF4J" | tail -20

hdr "3. ClickHouse — latest prices"
docker exec clickhouse clickhouse-client -q "
  SELECT symbol,
         argMaxMerge(price) AS price,
         max(updated)       AS updated
  FROM realtime.price_latest
  GROUP BY symbol
  ORDER BY symbol
  FORMAT PrettyCompact"

hdr "4. MinIO Bronze — partition directory layout"
docker run --rm --network platform-net --entrypoint sh minio/mc:RELEASE.2024-10-08T09-37-26Z \
  -c "mc alias set local http://minio:9000 minioadmin minioadmin123 >/dev/null 2>&1 && mc ls local/bronze/"

hdr "5. Airflow — last 3 runs per DAG"
docker exec airflow-scheduler airflow dags list-runs -d binance_klines_backfill 2>&1 \
  | grep -vE "FutureWarning|configuration.py" | head -6
docker exec airflow-scheduler airflow dags list-runs -d coingecko_snapshot 2>&1 \
  | grep -vE "FutureWarning|configuration.py" | head -6

hdr "6. Trino — Iceberg catalog schemas"
docker exec trino trino --catalog iceberg --execute "SHOW SCHEMAS" 2>&1 \
  | grep -vE "WARNING|jline"

hdr "7. Service-level healthcheck"
bash scripts/healthcheck.sh

echo ""
echo "${B}${G}Smoke test complete.${N}"
