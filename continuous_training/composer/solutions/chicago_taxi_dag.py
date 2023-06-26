# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""""DAG definition for Chicago Taxifare pipeline.
    This pipeline was created for use as a demo in the Data Engineering
    on GCP Course"""

import datetime
import logging
from base64 import b64encode as b64e

from airflow import DAG
from airflow.models import Variable

from airflow.contrib.operators.bigquery_check_operator import (
    BigQueryCheckOperator)
from airflow.contrib.operators.bigquery_check_operator import (
    BigQueryValueCheckOperator)
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.operators.bigquery_to_gcs import (
    BigQueryToCloudStorageOperator)
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.hooks.base_hook import BaseHook
from airflow.contrib.operators.pubsub_operator import PubSubPublishOperator
from airflow.utils.trigger_rule import TriggerRule

from airflow.contrib.operators.mlengine_operator import(
    MLEngineTrainingOperator)
from airflow.contrib.operators.mlengine_operator import MLEngineModelOperator
from airflow.contrib.operators.mlengine_operator import MLEngineVersionOperator

DEFAULT_ARGS = {
    'owner': 'Google Cloud Learner',
    'depends_on_past': False,
    'start_date': datetime.datetime(2020, 7, 1),
    'email': ['gcp.learning@fake-email.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=5)
}


def _get_project_id():
    """Get project ID from default Google Cloud connection."""

    extras = BaseHook.get_connection("google_cloud_default").extra_dejson
    key = "extra__google_cloud_platform__project"
    if key in extras:
        project_id = extras[key]
    else:
        raise ("Must configure project_id in google_cloud_default "
               "connection from Airflow Console")
    return project_id

PROJECT_ID = _get_project_id()

# Pub/Sub topic for publishing error and success messages.
TOPIC = "chicago-taxi-pipeline"

# Specify your source BigQuery project, dataset, and table names
SOURCE_BQ_PROJECT = "bigquery-public-data"
SOURCE_DATASET_TABLE_NAMES = "chicago_taxi_trips"
# Specify your destination BigQuery dataset
DESTINATION_DATASET = "chicago_taxi_ct"

# GCS bucket names and region, can also be changed.
BUCKET = "gs://" + PROJECT_ID
REGION = "us-central1"

# directory of the solution code base.
PACKAGE_URI = BUCKET + "/chicago_taxi/code/trainer.tar"
JOB_DIR = BUCKET + "/jobs"

model = "chicago_taxi_trips"

# TODO 1: Instaniate the DAG Object
with DAG(
        'chicago_taxi_dag',
        catchup=False,
        default_args=DEFAULT_ARGS,
        schedule_interval='@weekly') as dag:

    # SQL Query to check for fresh data. Data is considered "fresh" if it was
    # ingested within the past 90 days.
    check_sql = """
                SELECT
                    COUNT(*)
                FROM
                    `bigquery-public-data.chicago_taxi_trips.taxi_trips`
                WHERE
                    trip_start_timestamp >=
                        TIMESTAMP('{{ macros.ds_add(ds, -90) }}')
                """

    # BigQueryCheckOperator will fail if the result of the query is 0.
    # I.e. if there is no fresh data.
    bq_check_data_op = BigQueryCheckOperator(
        task_id="bq_check_data_task",
        use_legacy_sql=False,
        sql=check_sql,
    )

    CHECK_ERROR_MESSAGE = b64e(b'Error. Did not retrain on stale data.')

    # Task will only trigger if all upstream tasks fail. In which case a
    # message will be sent to the Pub/Sub topic specified above.

    publish_if_failed_check_op = PubSubPublishOperator(
        task_id="publish_on_failed_check_task",
        project=PROJECT_ID,
        topic=TOPIC,
        messages=[{'data': CHECK_ERROR_MESSAGE.decode()}],
        trigger_rule=TriggerRule.ALL_FAILED
    )

    # Base query to extract training and validation datasets from public
    # BigQuery dataset.
    bql = """
            SELECT
                (IFNULL(tolls,0) + fare) AS fare_amount,
                EXTRACT(DAYOFWEEK FROM trip_start_timestamp) AS dayofweek,
                EXTRACT(HOUR FROM trip_start_timestamp) AS hourofday,
                pickup_longitude AS pickuplon,
                pickup_latitude AS pickuplat,
                dropoff_longitude AS dropofflon,
                dropoff_latitude AS dropofflat,
                unique_key
            FROM
                `bigquery-public-data.chicago_taxi_trips.taxi_trips`
            WHERE
                trip_miles > 0
                AND fare >= 3.25
                AND fare <= 1000
                AND pickup_longitude > -89
                AND pickup_longitude < -85
                AND dropoff_longitude > -89
                AND dropoff_longitude < -85
                AND pickup_latitude > 38
                AND pickup_latitude < 44
                AND dropoff_latitude > 38
                AND dropoff_latitude < 44
                AND NOT (ROUND(pickup_longitude,4) = -87.6327
                         AND ROUND(pickup_latitude,4) = 41.8810
                         AND ROUND(dropoff_longitude,4) = -87.6327
                         AND ROUND(dropoff_latitude,4) = 41.8810)
                """

    # Query to take a 4/2500 sample of the results of the base query above for
    # the training dataset.
    bql_train = """
                SELECT fare_amount, dayofweek, hourofday, pickuplon, pickuplat,
                    dropofflon, dropofflat FROM({0}) WHERE
                MOD(ABS(FARM_FINGERPRINT(unique_key)), 2500) >= 1
                AND MOD(ABS(FARM_FINGERPRINT(unique_key)), 2500) <= 4
                """.format(bql)

    # Query to take a 1/2500 sample of the results of the base query above for
    # the training dataset.
    bql_valid = """
                SELECT fare_amount, dayofweek, hourofday, pickuplon, pickuplat,
                dropofflon, dropofflat FROM({0}) WHERE
                MOD(ABS(FARM_FINGERPRINT(unique_key)), 2500) = 5
                """.format(bql)

    # TODO 2: Fill in arguments for bq_train_data_op and bq_valid_data_op
    bq_train_data_op = BigQueryOperator(
        task_id="bq_train_data_task",
        bql=bql_train,
        destination_dataset_table="{}.{}_train_data"
                .format(DESTINATION_DATASET, model.replace(".", "_")),
        write_disposition="WRITE_TRUNCATE",  # specify to truncate on writes
        use_legacy_sql=False,
        dag=dag
    )

    bq_valid_data_op = BigQueryOperator(
        task_id="bq_eval_data_task",
        bql=bql_valid,
        destination_dataset_table="{}.{}_valid_data"
                .format(DESTINATION_DATASET, model.replace(".", "_")),
        write_disposition="WRITE_TRUNCATE",  # specify to truncate on writes
        use_legacy_sql=False,
        dag=dag
    )

    train_files = BUCKET + "/chicago_taxi/data/train/"
    valid_files = BUCKET + "/chicago_taxi/data/valid/"

    # Tasks to export the results of the previous BigQueryOperators to
    # Cloud Storage to stage for later AI Platform Training job.

    bq_export_train_csv_op = BigQueryToCloudStorageOperator(
        task_id="bq_export_gcs_train_csv_task",
        source_project_dataset_table="{}.{}_train_data"
                .format(DESTINATION_DATASET, model.replace(".", "_")),
        destination_cloud_storage_uris=[train_files +
                                        "{}/train-*.csv"
                                        .format(model.replace(".", "_"))],
        export_format="CSV",
        print_header=False,
        dag=dag
    )

    bq_export_valid_csv_op = BigQueryToCloudStorageOperator(
        task_id="bq_export_gcs_valid_csv_task",
        source_project_dataset_table="{}.{}_valid_data"
                .format(DESTINATION_DATASET, model.replace(".", "_")),
        destination_cloud_storage_uris=[valid_files +
                                        "{}/valid-*.csv"
                                        .format(model.replace(".", "_"))],
        export_format="CSV",
        print_header=False,
        dag=dag
    )

    # Python callable to set NEW_VERSION_NAME Airflow variable.
    def set_new_version_name(**kwargs):
        Variable.set("NEW_VERSION_NAME",
                     "v_{0}"
                     .format(datetime.datetime.now().strftime("%Y%m%d%H%M%S")))

    # TODO 3: Fill in arguments for python_new_version_name_op
    python_new_version_name_op = PythonOperator(
        task_id="python_new_version_name_task",
        python_callable=set_new_version_name,
        provide_context=True,
        dag=dag
        )

    # Arguments for MLEngineTrainingOperator
    job_id = "chicago_{}_{}".format(model.replace(".", "_"),
                                    datetime.datetime.now()
                                    .strftime("%Y%m%d%H%M%S"))
    output_dir = (BUCKET + "/chicago/trained_model/{}"
                  .format(model.replace(".", "_")))
    log_dir = (BUCKET + "/chicago/training_logs/{}"
                  .format(model.replace(".", "_")))
    job_dir = JOB_DIR + "/" + job_id

    # Arguments expected by the trainer package.
    training_args = [
        "--job-dir", job_dir,
        "--output_dir", output_dir,
        "--log_dir", log_dir,
        "--train_data_path", train_files + "chicago_taxi_trips/*.csv",
        "--eval_data_path", valid_files + "chicago_taxi_trips/*.csv",
        "--output_ds", f"{PROJECT_ID}.{DESTINATION_DATASET}",
        "--version_name", Variable.get('NEW_VERSION_NAME'),
    ]

    # BashOperator to remove the old SavedModel to ensure we are doing a
    # fresh run.
    bash_remove_trained_model_op = BashOperator(
        task_id="bash_remove_old_trained_model_{}_task"
                .format(model.replace(".", "_")),
        bash_command=("if gsutil ls {0} 2> /dev/null;"
                      "then gsutil -m rm -rf {0}/*; else true; fi"
                      .format(output_dir + model.replace(".", "_"))),
        dag=dag)

    # Task to submit AI Platform training job
    ml_engine_training_op = MLEngineTrainingOperator(
        task_id="ml_engine_training_{}_task".format(model.replace(".", "_")),
        project_id=PROJECT_ID,
        job_id=job_id,
        package_uris=[PACKAGE_URI],
        training_python_module="trainer.task",
        training_args=training_args,
        region=REGION,
        scale_tier="BASIC",
        runtime_version="2.1",
        python_version="3.7",
        dag=dag
     )

    # SQL Query to check if new model metrics satisfy conditions. Condition is
    # set to be high to ensure that the model likely meets the conditions.
    model_check_sql = """
                SELECT
                    IF(rmse - 10.0 >= 0, rmse - 10.0, 0) AS rmse
                FROM
                    `{0}.{1}.{2}`
                WHERE
                    version_name = '{3}'
                """.format(PROJECT_ID, DESTINATION_DATASET, 'model_metrics',
                           Variable.get("NEW_VERSION_NAME"))

    # TODO 4: Create bq_check_rmse_query_op
    bq_check_rmse_query_op = BigQueryValueCheckOperator(
        task_id="bq_value_check_rmse_task",
        sql=model_check_sql,
        pass_value=0,
        tolerance=0,
        use_legacy_sql=False,
    )

    VALUE_ERROR_MESSAGE = b64e(b'Error. Model RMSE > 10.0')

    # Task to report pipeline failure due to high RMSE
    publish_if_failed_value_check_op = PubSubPublishOperator(
        task_id="publish_on_failed_value_check_task",
        project=PROJECT_ID,
        topic=TOPIC,
        messages=[{'data': VALUE_ERROR_MESSAGE.decode()}],
        trigger_rule=TriggerRule.ALL_FAILED
    )

    MODEL_NAME = "chicago_taxi_trips"
    MODEL_LOCATION = BUCKET + "/chicago_taxi/saved_model/"

    # BashOperator to copy SavedModel into staging location for AI Platform
    bash_copy_saved_model_op = BashOperator(
        task_id="bash_copy_new_saved_model_{}_task"
                .format(model.replace(".", "_")),
        bash_command=("gsutil -m rsync -d -r {0} {1}"
                      .format(output_dir,
                              MODEL_LOCATION + model.replace(".", "_"))),
        dag=dag)

    # List currently existing models on AI Platform and pass to the next task
    # via the use of an XCom.

    bash_ml_engine_models_list_op = BashOperator(
        task_id="bash_ml_engine_models_list_{}_task"
                .format(model.replace(".", "_")),
        xcom_push=True,
        bash_command="gcloud ml-engine models list --filter='name:{0}'"
                     .format(MODEL_NAME),
        dag=dag
    )

    # Python callable which returns the appropriate task based on if the model
    # we want to deploy our new version to exists or not already.
    def check_if_model_already_exists(templates_dict, **kwargs):
        cur_model = MODEL_NAME
        ml_engine_models_list = kwargs["ti"].xcom_pull(
            task_ids="bash_ml_engine_models_list_{}_task".format(cur_model))
        logging.info(("check_if_model_already_exists:"
                      "{}: ml_engine_models_list = \n{}"
                     .format(cur_model, ml_engine_models_list)))
        create_model_task = ("ml_engine_create_model_{}_task"
                             .format(cur_model))
        dont_create_model_task = ("dont_create_model_dummy_{}_task"
                                  .format(cur_model))
        if (len(ml_engine_models_list) == 0 or
                ml_engine_models_list == "Listed 0 items."):
            return create_model_task
        else:
            return dont_create_model_task

    # BranchPythonOperator expectes an output of a task to trigger.
    check_if_model_exists_op = BranchPythonOperator(
        task_id="check_if_model_already_exists_{}_task"
                .format(model.replace(".", "_")),
        templates_dict={"model": model.replace(".", "_")},
        python_callable=check_if_model_already_exists,
        provide_context=True,
        dag=dag
    )

    # In case the model doesn't exist, using an MLEngineModelOperator to
    # create the new model.
    ml_engine_create_model_op = MLEngineModelOperator(
        task_id="ml_engine_create_model_{}_task"
                .format(model.replace(".", "_")),
        project_id=PROJECT_ID,
        model={"name": MODEL_NAME},
        operation="create",
        dag=dag
        )

    # NoOp in the case that the model already exists.
    dont_create_model_dummy_op = DummyOperator(
        task_id="dont_create_model_dummy_{}_task"
                .format(model.replace(".", "_")),
        dag=dag
    )

    # Set CURRENT_VERSION_NAME Airflow variable
    def set_current_version_name(**kwargs):
        Variable.set("CURRENT_VERSION_NAME",
                     Variable.get("NEW_VERSION_NAME"))

    # PythonOperator to run the above Python callable
    python_current_version_name_op = PythonOperator(
        task_id="python_curent_version_name_task",
        python_callable=set_current_version_name,
        provide_context=True,
        trigger_rule="none_failed",
        dag=dag
        )

    # MLEngineVersionOperator with operation set to "create" to create a new
    # version of our model
    ml_engine_create_version_op = MLEngineVersionOperator(
        task_id="ml_engine_create_version_{}_task"
                .format(model.replace(".", "_")),
        project_id=PROJECT_ID,
        model_name=MODEL_NAME,
        version_name=Variable.get("CURRENT_VERSION_NAME"),
        version={
            "name": Variable.get("CURRENT_VERSION_NAME"),
            "deploymentUri": MODEL_LOCATION + model.replace(".", "_"),
            "runtimeVersion": "2.1",
            "framework": "TENSORFLOW",
            "pythonVersion": "3.7",
            },
        operation="create",
        trigger_rule='none_failed',
        dag=dag
    )

    # MLEngineVersionOperator with operation set to "set_default" to set our
    # newly deployed version to be the default version.
    ml_engine_set_default_version_op = MLEngineVersionOperator(
        task_id="ml_engine_set_default_version_{}_task"
                .format(model.replace(".", "_")),
        project_id=PROJECT_ID,
        model_name=MODEL_NAME,
        version_name=Variable.get("NEW_VERSION_NAME"),
        version={"name": Variable.get("NEW_VERSION_NAME")},
        operation="set_default",
        dag=dag
    )

    SUCCESS_MESSAGE = b64e(b'Success. New model version deployed.')

    # Final task of the pipeline to publish a success message to Pub/Sub Topic
    publish_on_success_op = PubSubPublishOperator(
        task_id="publish_on_success_task",
        project=PROJECT_ID,
        topic=TOPIC,
        messages=[{'data': SUCCESS_MESSAGE.decode()}]
    )

    # TODO 5: Finish writing dependecies between bq_check_data_op and downstream ops.
    bq_check_data_op >> publish_if_failed_check_op
    bq_check_data_op >> python_new_version_name_op
    bq_check_data_op >> [bq_train_data_op, bq_valid_data_op]

    bq_train_data_op >> bq_export_train_csv_op
    bq_valid_data_op >> bq_export_valid_csv_op
    bq_check_data_op >>  bash_remove_trained_model_op
    [bq_export_train_csv_op, bq_export_valid_csv_op] >> ml_engine_training_op
    python_new_version_name_op >> ml_engine_training_op
    bash_remove_trained_model_op >> ml_engine_training_op

    ml_engine_training_op >> bq_check_rmse_query_op
    bq_check_rmse_query_op >> publish_if_failed_value_check_op

    bq_check_rmse_query_op >> python_current_version_name_op
    bq_check_rmse_query_op >>  bash_copy_saved_model_op
    bash_copy_saved_model_op >> ml_engine_create_version_op

    bq_check_rmse_query_op >> bash_ml_engine_models_list_op
    bash_ml_engine_models_list_op >> check_if_model_exists_op
    check_if_model_exists_op >> ml_engine_create_model_op
    check_if_model_exists_op >> dont_create_model_dummy_op
    ml_engine_create_model_op >> ml_engine_create_version_op
    dont_create_model_dummy_op >> ml_engine_create_version_op
    python_current_version_name_op >> ml_engine_create_version_op
    ml_engine_create_version_op >> ml_engine_set_default_version_op
    ml_engine_set_default_version_op >> publish_on_success_op
