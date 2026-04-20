from __future__ import annotations

import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC_RAW_TRADES", "raw_trades")
CHECKPOINT_URI = os.environ.get(
    "BRONZE_TRADES_CHECKPOINT", "s3a://checkpoints/bronze_trades/"
)
TABLE = os.environ.get("BRONZE_TRADES_TABLE", "iceberg.bronze.trades")
TRIGGER_SECS = int(os.environ.get("MICROBATCH_INTERVAL_SECS", "30"))
STARTING_OFFSETS = os.environ.get("STARTING_OFFSETS", "earliest")

TRADE_SCHEMA = StructType(
    [
        StructField("trade_id", LongType(), False),
        StructField("symbol", StringType(), False),
        StructField("price", DoubleType(), False),
        StructField("qty", DoubleType(), False),
        StructField("quote_qty", DoubleType(), False),
        StructField("trade_time_ms", LongType(), False),
        StructField("event_time_ms", LongType(), False),
        StructField("is_buyer_maker", BooleanType(), False),
        StructField("ingested_at", StringType(), False),
    ]
)


def ensure_table(spark: SparkSession) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS iceberg.bronze")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            trade_id         BIGINT,
            symbol           STRING,
            price            DOUBLE,
            qty              DOUBLE,
            quote_qty        DOUBLE,
            trade_time_ms    BIGINT,
            event_time_ms    BIGINT,
            is_buyer_maker   BOOLEAN,
            ingested_at      STRING,
            kafka_partition  INT,
            kafka_offset     BIGINT,
            kafka_timestamp  TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (symbol, days(kafka_timestamp))
        TBLPROPERTIES (
            'format-version' = '2',
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'zstd'
        )
        """
    )


def build_stream(spark: SparkSession):
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", STARTING_OFFSETS)
        .option("failOnDataLoss", "false")
        .load()
    )

    return raw.select(
        from_json(col("value").cast("string"), TRADE_SCHEMA).alias("v"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_timestamp"),
    ).select(
        "v.trade_id",
        "v.symbol",
        "v.price",
        "v.qty",
        "v.quote_qty",
        "v.trade_time_ms",
        "v.event_time_ms",
        "v.is_buyer_maker",
        "v.ingested_at",
        "kafka_partition",
        "kafka_offset",
        "kafka_timestamp",
    )


def main() -> None:
    spark = SparkSession.builder.appName("trades_to_iceberg_bronze").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    ensure_table(spark)

    query = (
        build_stream(spark)
        .writeStream.format("iceberg")
        .outputMode("append")
        .trigger(processingTime=f"{TRIGGER_SECS} seconds")
        .option("checkpointLocation", CHECKPOINT_URI)
        .toTable(TABLE)
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
