#!/bin/bash
/usr/local/bin/cloud_sql_proxy -dir=/var/run/cloud-sql-proxy -instances=$MLFLOW_SQL_CONNECTION_NAME=tcp:3306 &
sleep 5s
mlflow server --host=127.0.0.1 --port=80 --backend-store-uri=$MLFLOW_SQL_CONNECTION_STR --default-artifact-root=$MLFLOW_EXPERIMENTS_URI &

python task.py $@
#exec "$@"