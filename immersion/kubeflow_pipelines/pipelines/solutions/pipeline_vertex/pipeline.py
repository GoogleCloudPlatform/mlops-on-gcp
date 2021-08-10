# Copyright 2021 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at

# https://www.apache.org/licenses/LICENSE-2.0
    
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS"
# BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either 
# express or implied. See the License for the specific language governing 
# permissions and limitations under the License.
"""Kubeflow Covertype Pipeline."""
import os

from kfp import dsl
from kfp.components import create_component_from_func_v2

from tuning_lightweight_component import tune_hyperparameters
from training_lightweight_component import train_and_deploy


PIPELINE_ROOT = os.getenv('PIPELINE_ROOT')
PROJECT_ID = os.getenv('PROJECT_ID')
REGION = os.getenv('REGION')

TRAINING_CONTAINER_IMAGE_URI = os.getenv('TRAINING_CONTAINER_IMAGE_URI')
SERVING_CONTAINER_IMAGE_URI = os.getenv('SERVING_CONTAINER_IMAGE_URI')

TRAINING_FILE_PATH = os.getenv('TRAINING_FILE_PATH')
VALIDATION_FILE_PATH = os.getenv('VALIDATION_FILE_PATH')
#STAGING_BUCKET = os.getenv('STAGING_BUCKET')
#JOB_DIR = os.getenv('JOB_DIR')

MAX_TRIAL_COUNT = os.getenv('MAX_TRIAL_COUNT', 5)
PARALLEL_TRIAL_COUNT = os.getenv('PARALLEL_TRIAL_COUNT', 5)
THRESHOLD = os.getenv('THRESHOLD', 0.6)



tune_hpyerparameters_component = create_component_from_func_v2(
    tune_hyperparameters,
    base_image='python:3.8',
    output_component_file='covertype_kfp_tune_hyperparameters.yaml',
    packages_to_install=['google-cloud-aiplatform'],
)


train_and_deploy_component = create_component_from_func_v2(
    train_and_deploy,
    base_image='python:3.8',
    output_component_file='covertype_kfp_train_and_deploy.yaml',
    packages_to_install=['google-cloud-aiplatform'],

)


@dsl.pipeline(
    name="covertype-kfp-pipeline",
    description="The pipeline training and deploying the Covertype classifier",
    pipeline_root=PIPELINE_ROOT,
)
def covertype_train(
    training_container_uri: str=TRAINING_CONTAINER_IMAGE_URI,
    serving_container_uri: str=SERVING_CONTAINER_IMAGE_URI,
    training_file_path: str=TRAINING_FILE_PATH,
    validation_file_path: str=VALIDATION_FILE_PATH,
    #staging_bucket: str=STAGING_BUCKET,
    accuracy_deployment_threshold: float=THRESHOLD,
    max_trial_count: int=MAX_TRIAL_COUNT,
    parallel_trial_count: int=PARALLEL_TRIAL_COUNT,
    pipeline_root: str=PIPELINE_ROOT,
    #job_dir: str=JOB_DIR,
):
    staging_bucket = f'{pipeline_root}/staging'
    
    tuning_op = tune_hpyerparameters_component(
        project=PROJECT_ID,
        location=REGION,
        container_uri=training_container_uri,
        training_file_path=training_file_path,
        validation_file_path=VALIDATION_FILE_PATH,
        staging_bucket=staging_bucket,
        #job_dir=job_dir,
        max_trial_count=max_trial_count,
        parallel_trial_count=parallel_trial_count,
    )
    
    accuracy = tuning_op.outputs['best_acuracy']
    
    with dsl.Condition(accuracy >= accuracy_deployment_threshold, name="deploy_decision"):    
        train_and_deploy_op = train_and_deploy_component(
            project=PROJECT_ID,
            location=REGION,
            container_uri=training_container_uri,
            serving_container_uri=serving_container_uri,
            training_file_path=training_file_path,
            validation_file_path=validation_file_path,
            staging_bucket=staging_bucket,
            #job_dir=job_dir,
            alpha=tuning_op.outputs['best_alpha'], 
            max_iter=tuning_op.outputs['best_max_iter'],            
        )
