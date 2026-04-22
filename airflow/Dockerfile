FROM crypto-platform/spark:3.5.3 AS spark-dist

FROM apache/airflow:2.10.3-python3.11

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless procps \
 && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java

COPY --from=spark-dist --chown=airflow:root /opt/spark /opt/spark
ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$PATH

USER airflow
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
