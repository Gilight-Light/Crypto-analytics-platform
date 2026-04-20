from __future__ import annotations

import io
import logging
import os
from datetime import datetime

import boto3
import pandas as pd
import requests
from airflow.decorators import dag, task

log = logging.getLogger(__name__)

S3_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
S3_KEY = os.environ.get("MINIO_ROOT_USER", "minioadmin")
S3_SECRET = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")
BRONZE_BUCKET = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_PER_PAGE = 250


@dag(
    dag_id="coingecko_snapshot",
    description="Hourly snapshot of top-250 coins by market cap from CoinGecko.",
    schedule="@hourly",
    start_date=datetime(2026, 4, 1),
    catchup=False,
    max_active_runs=1,
    tags=["coingecko", "bronze", "batch"],
)
def coingecko_snapshot():
    @task
    def fetch_top_coins(**context) -> str:
        ds: str = context["ds"]
        logical_dt: datetime = context["logical_date"]
        ts_nodash: str = context["ts_nodash"]

        resp = requests.get(
            COINGECKO_MARKETS_URL,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": COINGECKO_PER_PAGE,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d",
            },
            headers={"accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        coins = resp.json()
        df = pd.DataFrame(coins)
        df["snapshot_ts"] = logical_dt

        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", compression="zstd", index=False)
        buf.seek(0)

        key = f"coingecko_top250/dt={ds}/hour={logical_dt.hour:02d}/{ts_nodash}.parquet"
        boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_KEY,
            aws_secret_access_key=S3_SECRET,
            region_name="us-east-1",
        ).put_object(Bucket=BRONZE_BUCKET, Key=key, Body=buf.getvalue())
        log.info("wrote s3://%s/%s (%d coins)", BRONZE_BUCKET, key, len(df))
        return f"s3://{BRONZE_BUCKET}/{key} — {len(df)} coins"

    fetch_top_coins()


coingecko_snapshot()
