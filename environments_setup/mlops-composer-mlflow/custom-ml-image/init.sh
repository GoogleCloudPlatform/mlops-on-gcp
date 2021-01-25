#!/bin/bash
export MLFLOW_GCS_ROOT_URI=gs://mlops-51-artifacts
export MLFLOW_SQL_CONNECTION_STR=mysql+pymysql://root:qweqwe123123@127.0.0.1:3306/mlflow
export MLFLOW_SQL_CONNECTION_NAME=edgeml-demo:us-central1:mlops-51-sql
export MLFLOW_EXPERIMENTS_URI=gs://mlops-51-artifacts/experiments
export MLFLOW_TRACKING_URI=http://127.0.0.1:80
export MLFLOW_TRACKING_EXTERNAL_URI=https://48a52c042ee8e9de-dot-us-central2.pipelines.googleusercontent.com
export MLOPS_COMPOSER_NAME=mlops-51-af
export MLOPS_REGION=us-central1
export ML_IMAGE_URI=gcr.io/edgeml-demo/mlops-51-mlimage:latest

/usr/local/bin/cloud_sql_proxy -dir=/var/run/cloud-sql-proxy -instances=edgeml-demo:us-central1:mlops-51-sql=tcp:3306 -credential_file=/usr/local/bin/sql-access.json &
sleep 5s
mlflow server --host=127.0.0.1 --port=80 --backend-store-uri=mysql+pymysql://root:qweqwe123123@127.0.0.1:3306/mlflow --default-artifact-root=gs://mlops-51-artifacts/experiments &
