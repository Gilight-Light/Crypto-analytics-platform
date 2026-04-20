FROM apache/hive:3.1.3

ARG POSTGRES_JDBC_VERSION=42.7.3
# hadoop-aws must match the Hadoop bundled in apache/hive:3.1.3 (Hadoop 3.1.0).
# hadoop-aws-3.3.x references IOStatisticsSource which 3.1.0 doesn't ship.
ARG HADOOP_AWS_VERSION=3.1.0
ARG AWS_SDK_VERSION=1.11.271

USER root
ADD https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar \
    /opt/hive/lib/postgresql-${POSTGRES_JDBC_VERSION}.jar
ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
    /opt/hive/lib/hadoop-aws-${HADOOP_AWS_VERSION}.jar
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar \
    /opt/hive/lib/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar
RUN chmod a+r /opt/hive/lib/postgresql-*.jar \
              /opt/hive/lib/hadoop-aws-*.jar \
              /opt/hive/lib/aws-java-sdk-bundle-*.jar

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
