from __future__ import annotations

from pyspark.sql import SparkSession


def main() -> None:
    spark = SparkSession.builder.appName("query_bronze").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    total = spark.sql("SELECT COUNT(*) AS n FROM iceberg.bronze.trades").collect()[0]["n"]
    print(f"\n=== iceberg.bronze.trades: {total:,} rows ===\n")

    spark.sql(
        """
        SELECT symbol,
               COUNT(*)                AS trades,
               ROUND(MIN(price), 4)    AS lo_price,
               ROUND(MAX(price), 4)    AS hi_price,
               MIN(kafka_timestamp)    AS first_seen,
               MAX(kafka_timestamp)    AS last_seen
        FROM   iceberg.bronze.trades
        GROUP  BY symbol
        ORDER  BY symbol
        """
    ).show(truncate=False)

    print("=== Snapshots ===")
    spark.sql("SELECT committed_at, snapshot_id, operation, summary['added-records'] AS added FROM iceberg.bronze.trades.snapshots ORDER BY committed_at").show(truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
