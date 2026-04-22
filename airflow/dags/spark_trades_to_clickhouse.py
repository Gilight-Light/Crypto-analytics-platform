from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

SPARK_DRIVER_HOST = os.environ.get("SPARK_DRIVER_HOST", "airflow-scheduler")

with DAG(
    dag_id="spark_trades_to_clickhouse",
    description="Kafka → ClickHouse streaming (manual trigger; runs until stopped).",
    schedule=None,
    start_date=datetime(2026, 4, 1),
    catchup=False,
    max_active_runs=1,
    tags=["spark", "streaming", "clickhouse"],
) as dag:
    SparkSubmitOperator(
        task_id="submit_trades_to_clickhouse",
        application="/opt/spark_jobs/streaming/trades_to_clickhouse.py",
        conn_id="spark_default",
        name="trades_to_clickhouse",
        deploy_mode="client",
        conf={
            "spark.driver.host": SPARK_DRIVER_HOST,
            "spark.cores.max": "1",
        },
    )
