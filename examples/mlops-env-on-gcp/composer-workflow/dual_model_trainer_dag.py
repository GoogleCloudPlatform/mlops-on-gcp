# [START dag_imports]
import datetime
import logging

from airflow import DAG
from airflow.models import Variable

# Working with Airflow 1.10.10 version!
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.operators.bigquery_table_delete_operator import BigQueryTableDeleteOperator
from airflow.contrib.operators.bigquery_to_gcs import BigQueryToCloudStorageOperator

# [END dag_imports]

# [START common dag_parameters]
# Airflow DAG execution interval. See details: https://airflow.apache.org/docs/stable/dag-run.html#cron-presets
INTERVAL = '@once'
START_DATE = datetime.datetime(2020, 9, 1)

PROJECT = "edgeml-demo"
LOCATION = "us-central"

# GCS folder where dataset CSV files are stored
DATASET_GCS_FOLDER = "gs://mlops-long-deployment-name-42-artifacts/data"
# Postfixes for temporary BQ tables and output CSV files
TRAINING_POSTFIX = "_training"
EVAL_POSTFIX = "_eval"
VALIDATION_POSTFIX = "_validation"

#
BQ_DATASET = "chicago_taxi_trips"
BQ_TABLE = "taxi_trips"

BQ_QUERY = """
SELECT unique_key, taxi_id, trip_start_timestamp, trip_end_timestamp, trip_seconds, trip_miles, pickup_census_tract, 
    dropoff_census_tract, pickup_community_area, dropoff_community_area, fare, tips, tolls, extras, trip_total, 
    payment_type, company, pickup_latitude, pickup_longitude, pickup_location, dropoff_latitude, dropoff_longitude, dropoff_location
FROM `bigquery-public-data.chicago_taxi_trips.taxi_trips` 
WHERE
  dropoff_latitude IS NOT NULL and
  dropoff_longitude IS NOT NULL and
  dropoff_location  IS NOT NULL and
  MOD(ABS(FARM_FINGERPRINT(unique_key)), 100) {}
LIMIT 100
"""

# [END dag_parameters]

# [START Python operator tasks]


def read_from_bigquery(**kwargs):
    return ""

# [END Python operator tasks]


# [START Airflow DAG]
with DAG('dual_model_trainer',
         description='Train evaluate and validate two models on taxi fare dataset. Select the best one and register it to Mlflow v0.21',
         schedule_interval=INTERVAL,
         start_date=START_DATE,
         catchup=False,
         doc_md=__doc__
         ) as dag:
    training_table_name = f"{PROJECT}.{BQ_DATASET}.{BQ_TABLE}{TRAINING_POSTFIX}"
    eval_table_name = f"{PROJECT}.{BQ_DATASET}.{BQ_TABLE}{EVAL_POSTFIX}"
    validation_table_name = f"{PROJECT}.{BQ_DATASET}.{BQ_TABLE}{VALIDATION_POSTFIX}"

    # Delete existing BQ tables
    traning_table_delete_task = BigQueryTableDeleteOperator(
        task_id="delete_trainingset",
        deletion_dataset_table=training_table_name,
        ignore_if_missing=True
    )
    eval_table_delete_task = BigQueryTableDeleteOperator(
        task_id="delete_evalset",
        deletion_dataset_table=eval_table_name,
        ignore_if_missing=True
    )
    validation_table_delete_task = BigQueryTableDeleteOperator(
        task_id="delete_validationset",
        deletion_dataset_table=validation_table_name,
        ignore_if_missing=True
    )

    # Copy Taxi table splits to user project BQ
    split_trainingset_task = BigQueryOperator(
        task_id="split_trainingset",
        use_legacy_sql=False,
        destination_dataset_table=training_table_name,
        sql=BQ_QUERY.format('between 0 and 80'),
        location=LOCATION
    )
    split_evalset_task = BigQueryOperator(
        task_id="split_evalset",
        use_legacy_sql=False,
        destination_dataset_table=eval_table_name,
        sql=BQ_QUERY.format('between 80 and 95'),
        location=LOCATION,
    )
    split_validationset_task = BigQueryOperator(
        task_id="split_validset",
        use_legacy_sql=False,
        destination_dataset_table=validation_table_name,
        sql=BQ_QUERY.format('between 95 and 100'),
        location=LOCATION,
    )

    # Extract BQ table splits to CSV files
    extract_trainingset_to_gcs_task = BigQueryToCloudStorageOperator(
        task_id="extract_trainingset_to_gcs",
        source_project_dataset_table=training_table_name,
        destination_cloud_storage_uris=[
            f"{DATASET_GCS_FOLDER}/ds{TRAINING_POSTFIX}.csv"],
        field_delimiter='|'
    )

    extract_evalset_to_gcs_task = BigQueryToCloudStorageOperator(
        task_id="extract_evalset_to_gcs",
        source_project_dataset_table=eval_table_name,
        destination_cloud_storage_uris=[
            f"{DATASET_GCS_FOLDER}/ds{EVAL_POSTFIX}.csv"],
        field_delimiter='|'
    )

    extract_validationset_to_gcs_task = BigQueryToCloudStorageOperator(
        task_id="extract_validationset_to_gcs",
        source_project_dataset_table=validation_table_name,
        destination_cloud_storage_uris=[
            f"{DATASET_GCS_FOLDER}/ds{VALIDATION_POSTFIX}.csv"],
        field_delimiter='|'
    )

    read_from_bigquery_task = PythonOperator(task_id='read_from_bigquery',
        python_callable=read_from_bigquery,
        provide_context=True,
        inlets={"auto": True})

    # Task order
    # Split public taxi fare estimation dataset to CSV files using Airflow BigQuery operators
    traning_table_delete_task >> split_trainingset_task >> extract_trainingset_to_gcs_task
    eval_table_delete_task >> split_evalset_task >> extract_evalset_to_gcs_task
    validation_table_delete_task >> split_validationset_task >> extract_validationset_to_gcs_task

    # Train two models on AI Platform Training jobs. Training process metrics are stored in Mlflow
    # ...

# [END Airflow DAG]

# Upload DAG
# gsutil cp dual_model_trainer_dag.py gs://us-central1-mlops-long-depl-2a6272ff-bucket/dags
