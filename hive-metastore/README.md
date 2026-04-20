# Hive Metastore

Standalone HMS acting as the **Iceberg catalog**. Spark, Trino, and dbt all
talk to it via Thrift on port 9083.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Extends `apache/hive:3.1.3` with PostgreSQL JDBC + hadoop-aws + aws-sdk-bundle. |
| `entrypoint.sh` | Idempotent schema init + start metastore. |
| `hive-site.xml` | JDBC connection, warehouse on S3A, thrift URI, S3A client settings. |

## Backend DB

HMS stores catalog metadata in a Postgres database named `hive`, created by
`postgres/init.sql` on first boot. The same Postgres instance also backs
Airflow and Superset (saves ~800MB RAM vs three separate instances).

## Warehouse

Table data lives on MinIO at `s3a://warehouse/`. HMS itself touches this bucket
on `CREATE DATABASE` / `CREATE TABLE` to `mkdir` the namespace directory — that's
why the Dockerfile bakes `hadoop-aws` + `aws-java-sdk-bundle` alongside the
Postgres JDBC driver. Data files themselves are written by the Iceberg client
(Spark / Trino), not HMS.

## Gotchas

- `SERVICE_OPTS` in `docker-compose.yml` overrides the JDBC values in
  `hive-site.xml` at runtime. Treat XML as documentation; `.env` is truth.
- First boot takes ~60–90s (JAR download + schema init). Compose healthcheck
  has `start_period: 90s`.
- `hadoop-aws` version MUST match the Hadoop version bundled in the Hive base
  image. `apache/hive:3.1.3` ships Hadoop 3.1.0; `hadoop-aws-3.3.x` references
  classes that don't exist there and won't load.
- To nuke and re-init: `make clean` (drops volumes), then `make up`.
