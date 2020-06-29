#!/bin/bash
. "${DL_ANACONDA_HOME}/etc/profile.d/conda.sh"
conda activate base
/usr/local/bin/cloud_sql_proxy -dir=/var/run/cloud-sql-proxy -instances=SQLINSTANCE=tcp:3306 &
mlflow server --host=127.0.0.1 --port=80 --backend-store-uri=mysql+pymysql://root:PASSWORD@127.0.0.1:3306/mlflow --default-artifact-root=gs://mlops19-mlflow &

exec "$@"