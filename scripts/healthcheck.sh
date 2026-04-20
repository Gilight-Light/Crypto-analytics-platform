#!/usr/bin/env bash
# Probe running stack: container state, service internals, host-to-container reachability.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -t 1 ]; then
  G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; C=$'\e[36m'
  DIM=$'\e[2m'; B=$'\e[1m'; N=$'\e[0m'
else
  G=''; R=''; Y=''; C=''; DIM=''; B=''; N=''
fi

PASS=0
FAIL=0
WARN=0

pass() { printf "  ${G}✓${N} %-22s ${DIM}%s${N}\n" "$1" "$2"; PASS=$((PASS+1)); }
fail() { printf "  ${R}✗${N} %-22s ${R}%s${N}\n"   "$1" "$2"; FAIL=$((FAIL+1)); }
warn() { printf "  ${Y}!${N} %-22s ${Y}%s${N}\n"   "$1" "$2"; WARN=$((WARN+1)); }

header() {
  printf "\n${B}${C}%s${N}\n" "$1"
  printf "${DIM}%s${N}\n" "────────────────────────────────────────────────"
}

for tool in docker nc curl; do
  command -v "$tool" >/dev/null 2>&1 || {
    printf "${R}Missing required tool: %s${N}\n" "$tool"
    exit 2
  }
done

if ! docker info >/dev/null 2>&1; then
  printf "${R}Docker daemon not reachable.${N} Start Docker Desktop and retry.\n"
  exit 2
fi

if [ -z "$(docker compose ps -q 2>/dev/null)" ]; then
  printf "${Y}Stack not running.${N} Run ${B}make up${N} first.\n"
  exit 2
fi

printf "${B}Crypto Analytics Platform — healthcheck${N}\n"
printf "${DIM}Project: %s${N}\n" "$(basename "$(pwd)")"

header "Container state"

container_state() {
  local svc="$1" expected_state="$2"
  local actual health exit_code
  actual=$(docker inspect --format='{{.State.Status}}' "$svc" 2>/dev/null || echo "missing")
  health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "$svc" 2>/dev/null || echo "missing")

  case "$expected_state" in
    running-healthy)
      if [ "$actual" = "running" ] && [ "$health" = "healthy" ]; then
        pass "$svc" "running, healthy"
      elif [ "$actual" = "running" ] && [ "$health" = "starting" ]; then
        warn "$svc" "running, health still starting"
      else
        fail "$svc" "state=$actual health=$health"
      fi
      ;;
    exited-ok)
      exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$svc" 2>/dev/null || echo "?")
      if [ "$actual" = "exited" ] && [ "$exit_code" = "0" ]; then
        pass "$svc" "one-shot job, exit 0"
      else
        fail "$svc" "state=$actual exit=$exit_code"
      fi
      ;;
  esac
}

container_state postgres       running-healthy
container_state minio          running-healthy
container_state kafka          running-healthy
container_state hive-metastore running-healthy
container_state minio-init     exited-ok

maybe_state() {
  local svc="$1" kind="$2"
  docker inspect "$svc" >/dev/null 2>&1 && container_state "$svc" "$kind"
}

maybe_state clickhouse                   running-healthy
maybe_state binance-producer             running-healthy
maybe_state spark-master                 running-healthy
maybe_state spark-worker                 running-healthy
maybe_state spark-streaming-bronze       running-healthy
maybe_state spark-streaming-clickhouse   running-healthy
maybe_state grafana                      running-healthy
maybe_state kafka-init                   exited-ok
maybe_state airflow-scheduler            running-healthy
maybe_state airflow-webserver            running-healthy
maybe_state airflow-init                 exited-ok
maybe_state trino                        running-healthy
maybe_state superset                     running-healthy
maybe_state superset-init                exited-ok

header "Service internals"

missing=""
for db in hive airflow superset; do
  if ! docker exec postgres psql -U platform -tAc \
       "SELECT 1 FROM pg_database WHERE datname='$db'" 2>/dev/null | grep -q 1; then
    missing="$missing $db"
  fi
done
if [ -z "$missing" ]; then
  pass "postgres.databases" "hive, airflow, superset present"
else
  fail "postgres.databases" "missing:$missing"
fi

hms_tables=$(docker exec postgres psql -U platform -d hive -tAc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null \
  | tr -d ' ' || echo "")
if [ -n "$hms_tables" ] && [ "$hms_tables" -ge 50 ] 2>/dev/null; then
  pass "hms.schema" "$hms_tables tables initialised"
elif [ -n "$hms_tables" ]; then
  warn "hms.schema" "only $hms_tables tables — schematool may have failed"
else
  fail "hms.schema" "could not query hive DB"
fi

if topics=$(docker exec kafka /opt/kafka/bin/kafka-topics.sh \
              --bootstrap-server localhost:9092 --list 2>/dev/null); then
  topic_count=$(printf '%s\n' "$topics" | grep -cve '^$' || true)
  pass "kafka.broker" "list OK ($topic_count topic(s))"
else
  fail "kafka.broker" "kafka-topics.sh failed"
fi

expected_buckets="bronze silver gold checkpoints warehouse"
if bucket_list=$(docker run --rm --network platform-net --entrypoint sh \
                   minio/mc:RELEASE.2024-10-08T09-37-26Z \
                   -c "mc alias set local http://minio:9000 minioadmin minioadmin123 >/dev/null 2>&1 && mc ls local/" \
                   2>/dev/null); then
  missing=""
  for b in $expected_buckets; do
    printf '%s\n' "$bucket_list" | grep -q "$b/" || missing="$missing $b"
  done
  if [ -z "$missing" ]; then
    pass "minio.buckets" "5/5 present (bronze, silver, gold, checkpoints, warehouse)"
  else
    fail "minio.buckets" "missing:$missing"
  fi
else
  fail "minio.buckets" "mc client could not connect"
fi

if docker inspect clickhouse >/dev/null 2>&1; then
  rows=$(docker exec clickhouse clickhouse-client -q "SELECT COUNT(*) FROM realtime.trades" 2>/dev/null || echo "?")
  if [ "$rows" != "?" ] && [ "$rows" -gt 0 ] 2>/dev/null; then
    pass "clickhouse.trades" "$rows rows in realtime.trades"
  elif [ "$rows" = "0" ]; then
    warn "clickhouse.trades" "no rows yet (streaming just started?)"
  else
    fail "clickhouse.trades" "could not query"
  fi
fi

if docker inspect trino >/dev/null 2>&1; then
  schemas=$(docker exec trino trino --catalog iceberg --execute "SHOW SCHEMAS" 2>/dev/null | grep -v information_schema | tr -d '"' | tr '\n' ' ')
  if [ -n "$schemas" ]; then
    pass "trino.iceberg" "schemas: $schemas"
  else
    fail "trino.iceberg" "could not list iceberg schemas"
  fi
fi

header "Host → container network"

tcp_check() {
  local label="$1" host="$2" port="$3"
  if nc -z -w 2 "$host" "$port" 2>/dev/null; then
    pass "$label" "$host:$port reachable"
  else
    fail "$label" "$host:$port UNREACHABLE"
  fi
}

http_check() {
  local label="$1" url="$2" expected="$3"
  local code
  code=$(curl -fsS -o /dev/null -w "%{http_code}" -m 3 "$url" 2>/dev/null || echo "000")
  if [ "$code" = "$expected" ]; then
    pass "$label" "HTTP $code $url"
  else
    fail "$label" "HTTP $code $url (expected $expected)"
  fi
}

tcp_check  "postgres"        localhost 15432
tcp_check  "kafka"           localhost 29092
tcp_check  "hive-metastore"  localhost 9083
http_check "minio.api"       "http://localhost:9000/minio/health/live" 200
http_check "minio.console"   "http://localhost:9001/" 200

docker inspect clickhouse      >/dev/null 2>&1 && http_check "clickhouse"    "http://localhost:8123/ping" 200
docker inspect grafana         >/dev/null 2>&1 && http_check "grafana"       "http://localhost:3000/api/health" 200
docker inspect spark-master    >/dev/null 2>&1 && http_check "spark.master"  "http://localhost:8080/" 200
docker inspect spark-worker    >/dev/null 2>&1 && http_check "spark.worker"  "http://localhost:8081/" 200
docker inspect airflow-webserver >/dev/null 2>&1 && http_check "airflow"    "http://localhost:8088/health" 200
docker inspect trino           >/dev/null 2>&1 && http_check "trino"         "http://localhost:8082/v1/info" 200
docker inspect superset        >/dev/null 2>&1 && http_check "superset"      "http://localhost:8089/health" 200

printf "\n${B}Summary:${N} "
printf "${G}%d passed${N}" "$PASS"
[ "$WARN" -gt 0 ] && printf ", ${Y}%d warning(s)${N}" "$WARN"
[ "$FAIL" -gt 0 ] && printf ", ${R}%d failure(s)${N}" "$FAIL"
printf "\n"

if [ "$FAIL" -eq 0 ]; then
  printf "${G}${B}All systems go.${N}\n"
  exit 0
else
  printf "${R}${B}Some checks failed.${N} Inspect with ${B}make logs${N} or ${B}docker compose ps${N}.\n"
  exit 1
fi
