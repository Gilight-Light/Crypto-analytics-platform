FROM apache/spark:3.5.3

USER root

ARG ICEBERG_VERSION=1.6.1
ARG SCALA_VERSION=2.12
ARG SPARK_VERSION=3.5.3
ARG KAFKA_CLIENTS_VERSION=3.5.1
ARG COMMONS_POOL2_VERSION=2.11.1
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_VERSION=1.12.262
ARG CLICKHOUSE_JDBC_VERSION=0.7.2

WORKDIR /opt/spark/jars

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_${SCALA_VERSION}/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_${SCALA_VERSION}-${ICEBERG_VERSION}.jar \
  ./iceberg-spark-runtime-3.5_${SCALA_VERSION}-${ICEBERG_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_${SCALA_VERSION}/${SPARK_VERSION}/spark-sql-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar \
  ./spark-sql-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_${SCALA_VERSION}/${SPARK_VERSION}/spark-token-provider-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar \
  ./spark-token-provider-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/${KAFKA_CLIENTS_VERSION}/kafka-clients-${KAFKA_CLIENTS_VERSION}.jar \
  ./kafka-clients-${KAFKA_CLIENTS_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/${COMMONS_POOL2_VERSION}/commons-pool2-${COMMONS_POOL2_VERSION}.jar \
  ./commons-pool2-${COMMONS_POOL2_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
  ./hadoop-aws-${HADOOP_AWS_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar \
  ./aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar

ADD --chown=spark:spark \
  https://repo1.maven.org/maven2/com/clickhouse/clickhouse-jdbc/${CLICKHOUSE_JDBC_VERSION}/clickhouse-jdbc-${CLICKHOUSE_JDBC_VERSION}-all.jar \
  ./clickhouse-jdbc-${CLICKHOUSE_JDBC_VERSION}-all.jar

RUN chmod a+r /opt/spark/jars/*.jar

USER spark
