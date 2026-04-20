#!/bin/bash
# Idempotent init: upstream 3.1.3 runs schematool -initSchema unconditionally
# and fails on restart. Check schema state first, only init when DB is blank.
set -e

export HIVE_CONF_DIR=/opt/hive/conf
export METASTORE_PORT="${METASTORE_PORT:-9083}"
export HADOOP_CLIENT_OPTS="-Xmx1G ${SERVICE_OPTS:-} ${HADOOP_CLIENT_OPTS:-}"

if /opt/hive/bin/schematool -dbType postgres -info 2>&1 | grep -q "Metastore schema version"; then
  echo ">>> Hive Metastore schema already initialised — skipping -initSchema"
else
  echo ">>> Metastore schema not present — running -initSchema"
  /opt/hive/bin/schematool -dbType postgres -initSchema
fi

echo ">>> Starting Hive Metastore Server on :${METASTORE_PORT}"
exec /opt/hive/bin/hive --skiphadoopversion --skiphbasecp --service metastore
