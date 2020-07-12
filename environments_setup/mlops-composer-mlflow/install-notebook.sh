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
  echo 'USAGE:  ./install-notebook.sh PROJECT_ID SQL_PASSWORD [DEPLOYMENT_NAME=mlops] [ZONE=us-central1-a]'
  echo 'PROJECT_ID      - GCP project Id'
  echo 'DEPLOYMENT_NAME - Short name prefix of infrastructure element and folder names, like SQL instance, Cloud Composer name'
  echo 'ZONE            - A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones'
  exit 1
fi

# Set script constants

PROJECT_ID=${1}
SQL_PASSWORD=${2}
DEPLOYMENT_NAME=${3:-mlops}
ZONE=${4:-us-central1-a}

# Set calculated infrastucture and folder names

SQL_USERNAME="root"
CLOUD_SQL="$DEPLOYMENT_NAME-sql"
# If you want to create multiple notebook instances each must have unique NOTEBOOK_NAME
GCS_BUCKET_NAME="gs://$DEPLOYMENT_NAME-artifact-store"
NB_IMAGE_URI="gcr.io/$PROJECT_ID/$DEPLOYMENT_NAME-mlimage:latest"

MLFLOW_SQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUD_SQL --format="value(connectionName)")
MLFLOW_SQL_CONNECTION_STR="mysql+pymysql://$SQL_USERNAME:$SQL_PASSWORD@127.0.0.1:3306/mlflow"

tput setaf 3; echo Creating environment
echo Project: $PROJECT_ID
echo Deployment name: $DEPLOYMENT_NAME
echo Zone: $ZONE
echo Cloud SQL name: $CLOUD_SQL
echo MLflow artifacts: $GCS_BUCKET_NAME
echo Setup started at:
date

tput setaf 7

# Set project
echo "Setting the project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

echo Build customized AI Platform Notebook docker image
gcloud builds submit custom-notebook --timeout 15m --tag ${NB_IMAGE_URI}

# Create connection info which will be used as environment variables inside the Notebook instance.
cat > custom-notebook/notebook-env.txt << EOF
MLFLOW_SQL_CONNECTION_STR=$MLFLOW_SQL_CONNECTION_STR
MLFLOW_SQL_CONNECTION_NAME=$MLFLOW_SQL_CONNECTION_NAME
MLFLOW_EXPERIMENTS_URI=${GCS_BUCKET_NAME}/experiments
MLFLOW_TRACKING_URI="https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
EOF

gsutil cp custom-notebook/notebook-env.txt $GCS_BUCKET_NAME
rm custom-notebook/notebook-env.txt

# Create Notebook instance
gcloud compute instances create $DEPLOYMENT_NAME-nb \
--zone $ZONE \
--image-family common-container \
--machine-type n1-standard-2 \
--image-project deeplearning-platform-release \
--maintenance-policy TERMINATE \
--boot-disk-device-name $DEPLOYMENT_NAME-disk \
--boot-disk-size 50GB \
--boot-disk-type pd-ssd \
--scopes cloud-platform,userinfo-email \
--metadata proxy-mode=service_account,container=$NB_IMAGE_URI,container-env-file=$GCS_BUCKET_NAME/notebook-env.txt

