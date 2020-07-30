#!/bin/bash

# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Check command line parameters
if [[ $# < 1 ]]; then
  echo 'USAGE:  ./set-env-vars.sh PROJECT_ID [DEPLOYMENT_NAME=mlops] [REGION=us-central1] [ZONE=us-central1-a]'
  echo 'PROJECT_ID      - GCP project Id'
  echo 'DEPLOYMENT_NAME - Short name prefix of infrastructure element and folder names, like SQL instance, Cloud Composer name'
  echo 'REGION          - A GCP region across the globe. Best to select one of the nearest.'
  echo 'ZONE            - A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones'
  exit 1
fi

# Set project and default constants
export PROJECT_ID=${1}
export DEPLOYMENT_NAME=${2:-mlops}
export REGION=${3:-us-central1}
export ZONE=${4:-us-central1-a}

export SQL_USERNAME="root"
# Set calculated infrastucture and folder names
export GCS_BUCKET_NAME="gs://$DEPLOYMENT_NAME-artifacts"
export NB_IMAGE_URI="gcr.io/$PROJECT_ID/$DEPLOYMENT_NAME-mlimage:latest"
export CLOUD_SQL="$DEPLOYMENT_NAME-sql"
export COMPOSER_NAME="$DEPLOYMENT_NAME-af"
export MLFLOW_IMAGE_URI="gcr.io/${PROJECT_ID}/$DEPLOYMENT_NAME"
export MLFLOW_PROXY_URI="gcr.io/${PROJECT_ID}/inverted-proxy"

tput setaf 3; echo Environment variables are set
echo Project \(PROJECT_ID\): $PROJECT_ID
echo Deployment name \(DEPLOYMENT_NAME\): $DEPLOYMENT_NAME
echo Zone \(ZONE\): $ZONE
echo Custom notebook docker image \(NB_IMAGE_URI\): $NB_IMAGE_URI
echo Cloud SQL name \(CLOUD_SQL\): $CLOUD_SQL
echo Cloud composer name \(COMPOSER_NAME\): $COMPOSER_NAME
echo MLflow artifacts GCS bucket \(GCS_BUCKET_NAME\): $GCS_BUCKET_NAME
echo MLflow serving docker image \(MLFLOW_IMAGE_URI\): $MLFLOW_IMAGE_URI
echo MLflow web proxy docker image \(MLFLOW_PROXY_URI\): $MLFLOW_PROXY_URI

tput setaf 7

# Set project
echo
echo "Setting the project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID
echo