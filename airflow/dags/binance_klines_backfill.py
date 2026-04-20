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

SYMBOLS = os.environ.get(
    "BINANCE_SYMBOLS", "btcusdt,ethusdt,solusdt,bnbusdt,xrpusdt"
).upper().split(",")

S3_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
S3_KEY = os.environ.get("MINIO_ROOT_USER", "minioadmin")
S3_SECRET = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")
BRONZE_BUCKET = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_COLS = [
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time_ms",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignored",
]


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_KEY,
        aws_secret_access_key=S3_SECRET,
        region_name="us-east-1",
    )


@dag(
    dag_id="binance_klines_backfill",
    description="Daily backfill of 1h OHLCV klines from Binance REST to MinIO Bronze.",
    schedule="@daily",
    start_date=datetime(2026, 4, 1),
    catchup=False,
    max_active_runs=1,
    tags=["binance", "bronze", "batch"],
)
def binance_klines_backfill():
    @task
    def fetch_symbol(symbol: str, **context) -> str:
        ds: str = context["ds"]
        end_dt = datetime.fromisoformat(ds)
        start_ms = int(end_dt.timestamp() * 1000) - 24 * 3600 * 1000
        end_ms = int(end_dt.timestamp() * 1000)

        resp = requests.get(
            BINANCE_KLINES_URL,
            params={
                "symbol": symbol,
                "interval": "1h",
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
            timeout=30,
        )
        resp.raise_for_status()
        klines = resp.json()

        df = pd.DataFrame(klines, columns=BINANCE_COLS).drop(columns=["ignored"])
        df["symbol"] = symbol
        for c in ("open", "high", "low", "close", "volume", "quote_volume",
                  "taker_buy_base", "taker_buy_quote"):
            df[c] = df[c].astype(float)
        for c in ("open_time_ms", "close_time_ms", "trades"):
            df[c] = df[c].astype("int64")

        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", compression="zstd", index=False)
        buf.seek(0)

        key = f"klines_1h/symbol={symbol}/dt={ds}/data.parquet"
        _s3_client().put_object(Bucket=BRONZE_BUCKET, Key=key, Body=buf.getvalue())
        log.info("wrote s3://%s/%s (%d rows)", BRONZE_BUCKET, key, len(df))
        return f"s3://{BRONZE_BUCKET}/{key} — {len(df)} rows"

    fetch_symbol.expand(symbol=SYMBOLS)


binance_klines_backfill()
