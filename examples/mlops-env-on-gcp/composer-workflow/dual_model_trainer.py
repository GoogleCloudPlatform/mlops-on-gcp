# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import datetime
import logging
import datetime
import time
from typing import List, Optional, Text, Union, Dict
import googleapiclient.discovery
from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.utils.trigger_rule import TriggerRule

# Working with Airflow 1.10.10 version!
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.hooks.bigquery_hook import BigQueryHook
from airflow.contrib.operators.bigquery_table_delete_operator import BigQueryTableDeleteOperator
from airflow.contrib.operators.bigquery_to_gcs import BigQueryToCloudStorageOperator
#from airflow.contrib.operators.dataflow_operator import DataflowTemplateOperator
#from airflow.contrib.operators.dataflow_operator import DataFlowPythonOperator


logger = logging.getLogger("airflow.task")

# [START common dag_parameters]
# Airflow DAG execution interval. See details: https://airflow.apache.org/docs/stable/dag-run.html#cron-presets
INTERVAL = "@once"
START_DATE = datetime.datetime(2020, 9, 1)

PROJECT_ID = os.getenv("GCP_PROJECT", "edgeml-demo")
REGION = os.getenv("COMPOSER_LOCATION", "us-central")
ZONE = os.getenv("COMPOSER_GKE_ZONE", "us-central1-a")
MLFLOW_GCS_ROOT_URI = os.getenv("MLFLOW_GCS_ROOT_URI", "")
REGMLFLOW_TRACKING_URIION = os.getenv("MLFLOW_TRACKING_URI", "")

# GCS folder where dataset CSV files are stored
#dags_folder = configuration.get('core', 'dags_folder')
DATASET_GCS_FOLDER = MLFLOW_GCS_ROOT_URI+"/data"
# Postfixes for temporary BQ tables and output CSV files
TRAINING_POSTFIX = "_training"
EVAL_POSTFIX = "_eval"
VALIDATION_POSTFIX = "_validation"

#
BQ_DATASET = "chicago_taxi_trips"
BQ_TABLE = "taxi_trips"

# Query used for Tensorflow data analytics step
BQ_QUERY_FOR_TFDV = """
SELECT unique_key, taxi_id, trip_start_timestamp, trip_end_timestamp, trip_seconds, trip_miles, pickup_census_tract, 
    dropoff_census_tract, pickup_community_area, dropoff_community_area, fare, tips, tolls, extras, trip_total, 
    payment_type, company, pickup_latitude, pickup_longitude, pickup_location, dropoff_latitude, dropoff_longitude, dropoff_location
FROM `bigquery-public-data.chicago_taxi_trips.taxi_trips` 
"""

BQ_QUERY = BQ_QUERY_FOR_TFDV + """
WHERE
  MOD(ABS(FARM_FINGERPRINT(unique_key)), 100) {}
LIMIT 10000
"""
#  dropoff_latitude IS NOT NULL and
#  dropoff_longitude IS NOT NULL and
#  dropoff_location  IS NOT NULL and


default_args = {
    'dataflow_default_options': {
        'project': PROJECT_ID,
        'region': REGION,
        'zone': ZONE,
        'tempLocation': MLFLOW_GCS_ROOT_URI+'/data-staging',
        }
    }

# [END dag_parameters]

# [START Python operator tasks]
def check_table_exists(**kwargs) -> str:
    hook = BigQueryHook(bigquery_conn_id='bigquery_default')
    table_exists = hook.table_exists(
        kwargs['project_id'], 
        kwargs['dataset_id'],
        kwargs['table_id'])
    logger.info("table_exists: %s", table_exists)
    return 'bq_data_statistics' if table_exists else 'bq_copy'

def run_analyzer(job_name,containerSpecGcsPath,
    source_path,output_path,baseline_stats_location=None,
    **kwargs
) -> Dict:
    """
    Runs the log analyzer Dataflow flex template.
    https://cloud.google.com/dataflow/docs/reference/rest/v1b3/projects.locations.flexTemplates/launch
    """

    service = googleapiclient.discovery.build('dataflow', 'v1b3')

    parameters = {
        'source_path' :source_path,
        'output_path': output_path,
    }

    if baseline_stats_location:
        parameters['baseline_stats_file'] = baseline_stats_location 
    body = {
        'launch_parameter': {
            'jobName': job_name,
            'parameters' : {
                'source_path' :source_path,
                'output_path': output_path,
            },
            'containerSpecGcsPath': containerSpecGcsPath
        }}

    request = service.projects().locations().flexTemplates().launch(
        location=REGION,
        projectId=PROJECT_ID,
        body=body)

    response = request.execute()
    return response
# [END Python operator tasks]

# [START Airflow DAG]
with DAG("dual_trainer_with_tfdv",
         description = "Train evaluate and validate two models on taxi fare dataset. Select the best one and register it to Mlflow v0.21",
         default_args = default_args,
         schedule_interval = INTERVAL,
         start_date = START_DATE,
         catchup = False,
         doc_md = __doc__
         ) as dag:
    dag.doc_md = __doc__

    copy_table_name = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}_analyzis"
    
    bq_check_table_exists = BranchPythonOperator(
        task_id='bq_check_table_exists',
        python_callable=check_table_exists,
        op_kwargs={
            'project_id':PROJECT_ID,
            'dataset_id':BQ_DATASET,
            'table_id':BQ_TABLE+'_analyzis',
        },
        provide_context=True)

    bq_copy = BigQueryOperator(
            task_id = "bq_copy",
            use_legacy_sql=False,
            destination_dataset_table = copy_table_name,
            sql = BQ_QUERY.format("between 0 and 10"),
            location = REGION)

    # File name must contains '*' when the output file size too large (~>240MB) e.g ds_bq_data_statistics_*.csv 
    bq_statistics_gcs_files = f"{DATASET_GCS_FOLDER}/stats_source/ds_bq_data_statistics_*.csv"
    bq_data_statistics = BigQueryToCloudStorageOperator(
            task_id = "bq_data_statistics",
            source_project_dataset_table = copy_table_name, # "bigquery-public-data.chicago_taxi_trips.taxi_trips",
            destination_cloud_storage_uris = [bq_statistics_gcs_files],
            field_delimiter = '|',
            # NONE_FAILED required since previous BigQueryOperator maybe SKIPped and not SUCCESS.
            trigger_rule= TriggerRule.NONE_FAILED)

    # Generates statistics by TFDV
    tfdv_statistics_task = PythonOperator(
        task_id = "tfdv_statistics_task",
        python_callable = run_analyzer,
        op_kwargs={
            # Note: containerSpecGcsPath points to file name created from _TEMPLATE_NAME variable in 'deploy_analyzer.sh'
            'containerSpecGcsPath' : MLFLOW_GCS_ROOT_URI+"/tfdv_csv_analyzer.json",
            'job_name' : f"{'analyzer'}-{time.strftime('%Y%m%d-%H%M%S')}",
            'source_path': bq_statistics_gcs_files,
            'output_path': f'{DATASET_GCS_FOLDER}/stats'
        },
        provide_context = True)

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
        logger.info("task: %s", task)
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

    # Exectute tasks
    for task in tasks:
        bq_check_table_exists >> bq_copy >> bq_data_statistics >> tfdv_statistics_task >> task["delete_table"] >> task["split_table"] >> task["extract_to_gcs"] 
    
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
