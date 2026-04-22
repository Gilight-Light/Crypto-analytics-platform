from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

SPARK_DRIVER_HOST = os.environ.get("SPARK_DRIVER_HOST", "airflow-scheduler")

with DAG(
    dag_id="spark_bronze_to_silver_trades",
    description="Hourly dedupe of Iceberg bronze.trades into silver.trades.",
    schedule="@hourly",
    start_date=datetime(2026, 4, 1),
    catchup=False,
    max_active_runs=1,
    tags=["spark", "batch", "iceberg", "silver"],
) as dag:
    SparkSubmitOperator(
        task_id="submit_bronze_to_silver",
        application="/opt/spark_jobs/batch/bronze_to_silver_trades.py",
        conn_id="spark_default",
        name="bronze_to_silver_trades",
        deploy_mode="client",
        conf={
            "spark.driver.host": SPARK_DRIVER_HOST,
            "spark.cores.max": "1",
        },
    )
