# Spark

Self-contained Spark image + config for the platform. Runs as a small
standalone cluster (1 master + 1 worker) on the `platform-net` Docker network.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Extends `apache/spark:3.5.3`; adds Iceberg, Kafka, S3A, AWS SDK jars. |
| `conf/spark-defaults.conf` | Platform-wide defaults: Iceberg catalog wired to HMS, S3A pointed at MinIO, small-RAM defaults. |

## Baked-in jars

| Jar | Version |
|---|---|
| `iceberg-spark-runtime-3.5_2.12` | 1.6.1 |
| `spark-sql-kafka-0-10_2.12` | 3.5.3 |
| `spark-token-provider-kafka-0-10_2.12` | 3.5.3 |
| `kafka-clients` | 3.5.1 |
| `commons-pool2` | 2.11.1 |
| `hadoop-aws` | 3.3.4 |
| `aws-java-sdk-bundle` | 1.12.262 |

Versions chosen to match Spark 3.5's bundled Hadoop 3.3.4. Bumping Iceberg
is generally safe within minor versions; bumping `hadoop-aws`/`aws-sdk` must
stay matched.

## Cluster topology

| Service | Role | Ports | RAM |
|---|---|---|---|
| `spark-master` | Coordinator | 7077 RPC, 8080 UI | ~512MB |
| `spark-worker` | Executor host | 8081 UI | ~1.5GB (configurable) |
| `spark-streaming-bronze` | Driver (client mode) running the trades streaming job | - | ~512MB |

UIs (after `make up PROFILES="streaming"`):
- Master: http://localhost:8080
- Worker: http://localhost:8081

## Submitting your own job

From any container on `platform-net`:

```bash
docker exec -it spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  /opt/spark_jobs/<your_job>.py
```

Jobs are mounted read-only at `/opt/spark_jobs` (bind-mounted from `./spark_jobs/` on host), so edits on host are picked up without rebuild.
