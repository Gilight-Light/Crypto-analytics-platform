from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, row_number, timestamp_millis
from pyspark.sql.window import Window


def main() -> None:
    spark = SparkSession.builder.appName("bronze_to_silver_trades").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    spark.sql("CREATE DATABASE IF NOT EXISTS iceberg.silver")

    bronze = spark.table("iceberg.bronze.trades")
    win = Window.partitionBy("symbol", "trade_id").orderBy(col("kafka_timestamp").desc())
    silver = (
        bronze.withColumn("rn", row_number().over(win))
        .where("rn = 1")
        .drop("rn")
        .withColumn("trade_time", timestamp_millis(col("trade_time_ms")))
        .withColumn("event_time", timestamp_millis(col("event_time_ms")))
        .select(
            "trade_id",
            "symbol",
            "price",
            "qty",
            "quote_qty",
            "trade_time",
            "event_time",
            "is_buyer_maker",
            "kafka_timestamp",
        )
    )

    (
        silver.writeTo("iceberg.silver.trades")
        .using("iceberg")
        .tableProperty("format-version", "2")
        .tableProperty("write.format.default", "parquet")
        .tableProperty("write.parquet.compression-codec", "zstd")
        .partitionedBy(col("symbol"))
        .createOrReplace()
    )

    n_bronze = bronze.count()
    n_silver = spark.table("iceberg.silver.trades").count()
    print(f"bronze rows: {n_bronze:,}   silver rows: {n_silver:,}")

    spark.stop()


if __name__ == "__main__":
    main()
