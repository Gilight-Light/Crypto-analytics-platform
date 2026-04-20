from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json, timestamp_millis, to_timestamp
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
    "CLICKHOUSE_TRADES_CHECKPOINT", "s3a://checkpoints/clickhouse_trades/"
)
CH_JDBC_URL = os.environ.get(
    "CLICKHOUSE_JDBC_URL", "jdbc:clickhouse://clickhouse:8123/realtime"
)
CH_USER = os.environ.get("CLICKHOUSE_USER", "default")
CH_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "")
CH_TABLE = os.environ.get("CLICKHOUSE_TRADES_TABLE", "realtime.trades")
TRIGGER_SECS = int(os.environ.get("MICROBATCH_INTERVAL_SECS", "10"))
STARTING_OFFSETS = os.environ.get("STARTING_OFFSETS", "latest")

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


def build_stream(spark: SparkSession) -> DataFrame:
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
        col("v.trade_id").alias("trade_id"),
        col("v.symbol").alias("symbol"),
        col("v.price").alias("price"),
        col("v.qty").alias("qty"),
        col("v.quote_qty").alias("quote_qty"),
        timestamp_millis(col("v.trade_time_ms")).alias("trade_time"),
        timestamp_millis(col("v.event_time_ms")).alias("event_time"),
        col("v.is_buyer_maker").cast("int").alias("is_buyer_maker"),
        to_timestamp(col("v.ingested_at")).alias("ingested_at"),
        col("kafka_partition"),
        col("kafka_offset"),
        col("kafka_timestamp"),
    )


def write_to_clickhouse(df: DataFrame, _batch_id: int) -> None:
    (
        df.write.format("jdbc")
        .option("url", CH_JDBC_URL)
        .option("driver", "com.clickhouse.jdbc.ClickHouseDriver")
        .option("dbtable", CH_TABLE)
        .option("user", CH_USER)
        .option("password", CH_PASSWORD)
        .option("batchsize", "2000")
        .option("isolationLevel", "NONE")
        .mode("append")
        .save()
    )


def main() -> None:
    spark = SparkSession.builder.appName("trades_to_clickhouse").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    query = (
        build_stream(spark)
        .writeStream.foreachBatch(write_to_clickhouse)
        .outputMode("append")
        .trigger(processingTime=f"{TRIGGER_SECS} seconds")
        .option("checkpointLocation", CHECKPOINT_URI)
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
