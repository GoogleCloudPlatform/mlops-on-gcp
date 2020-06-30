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
  echo 'USAGE:  ./install.sh PROJECT_ID SQL_PASSWORD [DEPLOYMENT_NAME=mlops] [REGION=us-central1] [ZONE=us-central1-a]'
  echo 'PROJECT_ID      - GCP project Id'
  echo 'DEPLOYMENT_NAME - Short name prefix of infrastructure element and folder names, like SQL instance, Cloud Composer name'
  echo 'REGION          - A GCP region across the globe. Best to select one of the nearest.'
  echo 'ZONE            - A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones'
  exit 1
fi

# Set script constants

PROJECT_ID=${1}
SQL_PASSWORD=${2}
export DEPLOYMENT_NAME=${3:-mlops}
export REGION=${4:-us-central1} 
export ZONE=${5:-us-central1-a}

# Set calculated infrastucture and folder names

export SQL_USERNAME="root"
export CLOUD_SQL="$DEPLOYMENT_NAME-sql"
export COMPOSER_NAME="$DEPLOYMENT_NAME-af"
export GCS_BUCKET_NAME="gs://$DEPLOYMENT_NAME-artifact-store"
export MLFLOW_IMAGE_URI="gcr.io/${PROJECT_ID}/$DEPLOYMENT_NAME"


tput setaf 3; echo Creating environment
echo Project: $PROJECT_ID
echo Deployment name: $DEPLOYMENT_NAME
echo Region: $REGION, zone: $ZONE
echo Cloud SQL name: $CLOUD_SQL
echo MLflow artifacts: $GCS_BUCKET_NAME
echo Composer name: $COMPOSER_NAME
echo Setup started at:
date

tput setaf 7

# Set project
echo Setting the project to: $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable services
echo Enabling all required services

gcloud services enable \
cloudbuild.googleapis.com \
sourcerepo.googleapis.com \
container.googleapis.com \
compute.googleapis.com \
composer.googleapis.com \
containerregistry.googleapis.com \
dataflow.googleapis.com \
sqladmin.googleapis.com \
notebooks.googleapis.com

echo Required services enabled
echo 

#echo Create GCS bucket

if ! gsutil list "$GCS_BUCKET_NAME"; then
gsutil mb -p $PROJECT_ID -l $REGION $GCS_BUCKET_NAME
fi

# Cloud SQL

if [[ $(gcloud sql instances list --filter="$CLOUD_SQL" --format='value(name)') != "$CLOUD_SQL" ]]; then
    echo Provisioning Cloud SQL with name '$CLOUD_SQL'
    gcloud sql instances create $CLOUD_SQL --tier=db-g1-small --region=$REGION
    gcloud sql databases create mlflow --instance=$CLOUD_SQL
    gcloud sql users set-password $SQL_USERNAME --host=% --instance=$CLOUD_SQL --password=$SQL_PASSWORD
fi
CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUD_SQL --format="value(connectionName)")
echo Cloud SQL provisioned

# Cloud Composer

if [[ $(gcloud composer environments list --locations=$REGION --filter="$COMPOSER_NAME" --format='value(name)') != "$COMPOSER_NAME" ]]; then
    echo Provisioing Cloud Composer
    gcloud composer environments create $COMPOSER_NAME \
    --location=$REGION \
    --zone=$ZONE \
    --airflow-configs=core-dags_are_paused_at_creation=True \
    --disk-size=20GB \
    --image-version=composer-1.10.4-airflow-1.10.6 \
    --machine-type=n1-standard-2 \
    --node-count=3 \
    --python-version=3 \
    --enable-ip-alias

    # Install Python packages
    echo Install Python packages to Cloud Composer
    gcloud composer environments update $COMPOSER_NAME \
    --update-pypi-packages-from-file=requirements.txt \
    --location=$REGION

fi
echo Cloud Composer provisioned and Python packages installed
echo

echo Provisioning MLflow Tracking server

# Set local Kubernetes configuration to connect to Composer GKE cluster

GKE_CLUSTER=$(gcloud container clusters list --limit=1 --zone=$ZONE --filter="name~$COMPOSER_NAME" --format="value(name)")
gcloud container clusters get-credentials $GKE_CLUSTER --zone $ZONE  --project $PROJECT_ID

SA_EMAIL=sql-proxy-access@$PROJECT_ID.iam.gserviceaccount.com
if [[ $(gcloud iam service-accounts list --filter="$SA_EMAIL" --format='value(email)') != "$SA_EMAIL" ]]; then
    echo Create new service account: '$SA_EMAIL'
    gcloud iam service-accounts create sql-proxy-access --format='value(email)' --display-name="Cloud SQL access for sql proxy"
fi

if [[ -e mlflow-helm/sql-access.json ]]; then
    echo Service account key already exists: mlflow-helm/sql-access.json
else
    gcloud iam service-accounts keys create mlflow-helm/sql-access.json --iam-account=$SA_EMAIL
fi

gcloud projects add-iam-policy-binding $PROJECT_ID \
--member serviceAccount:$SA_EMAIL \
--role roles/cloudsql.client

# Build MLflow docker image

gcloud builds submit mlflow-helm/docker --timeout 15m --tag ${MLFLOW_IMAGE_URI}:latest

# Using fix K8s namespace: 'mlflow' for MLflow
kubectl create namespace mlflow || echo mlflow namespace exists

helm install mlflow --namespace mlflow \
--set image.repository=$MLFLOW_IMAGE_URI \
--set defaultArtifactRoot=$GCS_BUCKET_NAME \
--set backendStore.mysql.host="127.0.0.1" \
--set backendStore.mysql.port="3306" \
--set backendStore.mysql.database="mlflow" \
--set backendStore.mysql.username=$SQL_USERNAME \
--set backendStore.mysql.password=$SQL_PASSWORD \
--set cloudSqlInstance.name=$CLOUD_SQL_CONNECTION_NAME \
mlflow-helm

# Generate command for debug:
#echo Template command
#echo helm template mlflow --namespace mlflow --set image.repository=$MLFLOW_IMAGE_URI --set defaultArtifactRoot=$GCS_BUCKET_NAME --set backendStore.mysql.host="127.0.0.1" --set backendStore.mysql.port="3306" --set backendStore.mysql.database="mlflow" --set backendStore.mysql.user=$SQL_USERNAME --set backendStore.mysql.password=$SQL_PASSWORD --set cloudSqlInstance.name=$CLOUD_SQL_CONNECTION_NAME --output-dir './yamls' mlflow-helm

echo MLflow Tracking server provisioned
