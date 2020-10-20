# [START dag_imports]
import os
import datetime
import logging
import tensorflow_data_validation as tfdv
import airflow
from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator

# Working with Airflow 1.10.10 version!
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.operators.bigquery_table_delete_operator import BigQueryTableDeleteOperator
from airflow.contrib.operators.bigquery_to_gcs import BigQueryToCloudStorageOperator

# [END dag_imports]

# [START common dag_parameters]
# Airflow DAG execution interval. See details: https://airflow.apache.org/docs/stable/dag-run.html#cron-presets
INTERVAL = "@once"
START_DATE = datetime.datetime(2020, 9, 1)

PROJECT_ID = os.getenv("GCP_PROJECT", "edgeml-demo")
REGION = os.getenv("COMPOSER_LOCATION", "us-central")

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


def generate_tfdv_statistics(gcs_file_name):
    logging.info("Processing %s", gcs_file_name)
    train_stats = tfdv.generate_statistics_from_csv(gcs_file_name)
    tfdv.WriteStatisticsToTFRecord(output_path = gcs_file_name + ".tfrecord")
    return None

# [END Python operator tasks]


# [START Airflow DAG]
with DAG("dual_model_trainer",
         description = "Train evaluate and validate two models on taxi fare dataset. Select the best one and register it to Mlflow v0.02",
         schedule_interval = INTERVAL,
         start_date = START_DATE,
         catchup = False,
         doc_md = __doc__
         ) as dag:
    
    tasks = [{
            "postfix" : "training",
            "dataset_range" : "between 0 and 80"
        },{
            "postfix" : "eval",
            "dataset_range" : "between 80 and 95"
        },{
            "postfix" : "validation",
            "dataset_range" : "between 95 and 100"
        }]
    
    # Define task list
    for task in tasks:
        logging.info("task: %s", task)
        postfix = task.get("postfix")
        # Note: fix table names causes race condition in case when DAG triggered before the previous finished.
        table_name = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}_{postfix}"
        gcs_file_name = f"{DATASET_GCS_FOLDER}/ds_{postfix}.csv"
        
        # Deletes previous training temporary tables
        task["delete_table"] = BigQueryTableDeleteOperator(
            task_id = "delete_table_" + postfix,
            deletion_dataset_table = table_name,
            ignore_if_missing = True)

        # Splits and copy source BQ table to 'dataset_range' sized segments
        task["split_table"] = BigQueryOperator(
            task_id = "split_table_" + postfix,
            use_legacy_sql=False,
            destination_dataset_table = table_name,
            sql = BQ_QUERY.format(task["dataset_range"]),
            location = REGION)
        
        # Extract split tables to CSV files in GCS
        task["extract_to_gcs"] = BigQueryToCloudStorageOperator(
            task_id = "extract_to_gcs_" + postfix,
            source_project_dataset_table = table_name,
            destination_cloud_storage_uris = [gcs_file_name],
            field_delimiter = '|')
        
        # Generates statisctics by TFDV
        task["tfdv_statisctics"] = PythonOperator(
            task_id = "tfdv_statistics_for_" + postfix,
            python_callable = generate_tfdv_statistics,
            provide_context = True,
            op_kwargs={'gcs_file_name': gcs_file_name})

    # Exectute tasks
    for task in tasks:
        task["delete_table"] >> task["split_table"] >> task["extract_to_gcs"] >> task["tfdv_statisctics"]
    
    # Train two models (two separate AI Platform Training Jobs) (PythonOperator)
    #  Input: data in GCS
    #  Output: model1.joblib model2.joblib
    #  Note: eval metric (one eval split) is stored in MLflow

    # Evaluate the previous model on the current  eval split
    #  Input: experiment Id (fetch the last (registered) model)
    #  Output: eval stored in MLflow for the previous model

    # Validate the model (PythonOperator)
    #  Input: Mflow metric
    #  Output: which model (path) to register

    # Register the model (PythonOperator) 
    #  Input: Path of the winning model
    #  Output: Model in specific GCS location

# [END Airflow DAG]

# Upload DAG
# gsutil cp dual_model_trainer_dag.py gs://us-central1-mlops-long-depl-2a6272ff-bucket/dags
