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

# Common error handler

# Set up a global error handler
err_handler() {
    echo "Error on line: $1"
    echo "Caused by: $2"
    echo "That returned exit status: $3"
    echo "Aborting..."
    exit $3
}

trap 'err_handler "$LINENO" "$BASH_COMMAND" "$?"' ERR

# Check command line parameters
if [[ $# < 2 ]]; then
  echo 'USAGE:  ./destroy.sh PROJECT_ID [DEPLOYMENT_NAME=mlops] [REGION=us-central1] [ZONE=us-central1-a]'
  echo 'PROJECT_ID      - GCP project Id'
  echo 'DEPLOYMENT_NAME - Short name prefix of infrastucture element and folder names, like SQL instance, Cloud Composer name'
  echo 'REGION          - A GCP region across the globe. Best to select one of the nearest.'
  echo 'ZONE            - A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones'
  exit 1
fi

# Set script constants

PROJECT_ID=${1}
export DEPLOYMENT_NAME=${2:-mlops}
export REGION=${3:-us-central1} 
export ZONE=${4:-us-central1-a}

# Set calculated infrastucture and folder names

export CLOUD_SQL="$DEPLOYMENT_NAME-sql"
export COMPOSER_NAME="$DEPLOYMENT_NAME-af"
export NOTEBOOK_NAME="$DEPLOYMENT_NAME-nb"

tput setaf 3; echo Creating environment
echo Project: $PROJECT_ID
echo Deployment name: $DEPLOYMENT_NAME
echo Region: $REGION, zone: $ZONE
echo Cloud SQL name: $CLOUD_SQL
echo Notebook name: $NOTEBOOK_NAME
echo Composer name: $COMPOSER_NAME

tput setaf 7

# Set project
echo Setting the project to: $PROJECT_ID
gcloud config set project $PROJECT_ID

# Cloud Composer

if [[ $(gcloud composer environments list --locations=$REGION --filter="$COMPOSER_NAME" --format='value(name)') == "$COMPOSER_NAME" ]]; then
    echo Delete Cloud Composer
    gcloud composer environments delete $COMPOSER_NAME --location=$REGION
    echo Cloud Composer deleted. MLflow also deleted with Composer.
fi

SA_EMAIL=sql-proxy-access@$PROJECT_ID.iam.gserviceaccount.com
if [[ $(gcloud iam service-accounts list --filter="$SA_EMAIL" --format='value(email)') == "$SA_EMAIL" ]]; then
    echo Delete service account: '$SA_EMAIL'
    gcloud iam service-accounts delete $SA_EMAIL
    rm -f mlflow-helm/sql-access.json
fi

# Cloud SQL

if [[ $(gcloud sql instances list --filter="$CLOUD_SQL" --format='value(name)') == "$CLOUD_SQL" ]]; then
    echo Delete Cloud SQL with name '$CLOUD_SQL'
    gcloud sql instances delete $CLOUD_SQL
    echo Cloud SQL deleted
fi

# Temporary removed: delete notebook is not working (location ZONE vs. REGION issue).
# echo Delete Notebook with name '$NOTEBOOK_NAME'
# gcloud beta notebooks instances delete $NOTEBOOK_NAME --location=$ZONE
