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


# Set up a global error handler
err_handler() {
    echo "Error on line: $1"
    echo "Caused by: $2"
    echo "That returned exit status: $3"
    echo "Aborting..."
    return $3
}

# Check command line parameters
if [[ $# < 2 ]]; then
  echo 'USAGE:  ./install.sh PROJECT_ID SQL_PASSWORD [DEPLOYMENT_NAME=mlops] [REGION=us-central1] [ZONE=us-central1-a]'
  echo 'PROJECT_ID      - GCP project Id'
  echo 'SQL_PASSWORD    - Password to connect database'
  echo 'DEPLOYMENT_NAME - Short name prefix of infrastructure element and folder names, like SQL instance, Cloud Composer name. Default: mlflow'
  echo 'REGION          - A GCP region across the globe. Best to select one of the nearest. Default: us-central-1'
  echo 'ZONE            - A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones. Default: us-central1-a'
  return 1
fi

# Set script constants
SQL_PASSWORD=${2}
source set-env-vars.sh ${1} ${3} ${4} ${5}
if [ $? -ne 0 ]; then
  echo "Error"
  return 1
fi

trap 'err_handler "$LINENO" "$BASH_COMMAND" "$?"' ERR

tput setaf 3; echo Creating environment
echo Setup started at:
date
tput setaf 7

# 1. Enable services

echo "Enabling all required services..."

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

echo "Required services enabled."
echo

#2. Creating GCS bucket

echo "Creating GCS bucket for artifacts..."
if ! gsutil list "$GCS_BUCKET_NAME"; then
gsutil mb -p $PROJECT_ID -l $REGION $GCS_BUCKET_NAME
fi
echo "GCS bucket available: $GCS_BUCKET_NAME"
echo

# 3. Creating Cloud SQL

if [[ $(gcloud sql instances list --filter="$CLOUD_SQL" --format='value(name)') != "$CLOUD_SQL" ]]; then
    echo "Provisioning Cloud SQL..."
    gcloud sql instances create $CLOUD_SQL --tier=db-g1-small --region=$REGION
    gcloud sql databases create mlflow --instance=$CLOUD_SQL
    gcloud sql users set-password $SQL_USERNAME --host=% --instance=$CLOUD_SQL --password=$SQL_PASSWORD
fi
MLFLOW_SQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUD_SQL --format="value(connectionName)")
echo "Cloud SQL is available: $MLFLOW_SQL_CONNECTION_NAME"

# 4. Provisioning Composer cluster

# Creating Cloud Composer
if [[ $(gcloud composer environments list --locations=$REGION --filter="$COMPOSER_NAME" --format='value(name)') != "$COMPOSER_NAME" ]]; then
    echo "Provisioing Cloud Composer..."
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
fi
echo "Cloud Composer is available: $COMPOSER_NAME"
echo

# Installing Python packages to Composer
echo "Install Python packages to Cloud Composer..."
gcloud composer environments update $COMPOSER_NAME \
  --update-pypi-packages-from-file=composer-requirements.txt \
  --location=$REGION
echo

# 5. Installing MLflow to Composer

echo "Provisioning MLflow Tracking server..."

# Set local Kubernetes configuration to connect to Composer GKE cluster
echo "Setting configuration to connect to Composer GKE cluster..."
GKE_CLUSTER=$(gcloud container clusters list --limit=1 --zone=$ZONE --filter="name~$COMPOSER_NAME" --format="value(name)")
gcloud container clusters get-credentials $GKE_CLUSTER --zone $ZONE  --project $PROJECT_ID

# Create service account
SA_EMAIL=sql-proxy-access@$PROJECT_ID.iam.gserviceaccount.com
if [[ $(gcloud iam service-accounts list --filter="$SA_EMAIL" --format='value(email)') != "$SA_EMAIL" ]]; then
    echo "Create new service account: $SA_EMAIL"
    gcloud iam service-accounts create sql-proxy-access --format='value(email)' --display-name="Cloud SQL access for sql proxy"
fi

# Download service account key
if [[ -e mlflow-helm/sql-access.json ]]; then
    echo "Service account key already exists: mlflow-helm/sql-access.json"
else
    gcloud iam service-accounts keys create mlflow-helm/sql-access.json --iam-account=$SA_EMAIL
fi

# Set role to the service account
echo "Set cloudsql.client role to the service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
--member serviceAccount:$SA_EMAIL \
--role roles/cloudsql.client
echo "IAM policy binding is added."

# Build MLflow docker image
echo "Build MLflow Docker container image..."
gcloud builds submit mlflow-helm/docker --timeout 15m --tag ${MLFLOW_IMAGE_URI}:latest
echo "MLflow Docker container image is built: ${MLFLOW_IMAGE_URI}:latest"

# Build MLflow UI proxy image
echo "Build MLflow UI proxy container image..."
gcloud builds submit mlflow-helm/proxy --timeout 15m --tag ${MLFLOW_PROXY_URI}:latest
echo "MLflow UI proxy container image is built: ${MLFLOW_PROXY_URI}:latest"

# Initializing Helm's tiller
echo "Initializing Helm environment..."
kubectl create serviceaccount --namespace kube-system tiller
kubectl create clusterrolebinding tiller-cluster-rule --clusterrole=cluster-admin --serviceaccount=kube-system:tiller

# Using fix K8s namespace: 'mlflow' for MLflow
echo "Create mlfow namespace to the GKE cluster..."
kubectl create namespace mlflow || echo "mlflow namespace exists"

# Deploying mlflow using helm
echo "Deploying mlflow helm configuration..."
helm install mlflow --namespace mlflow \
--set images.mlflow=$MLFLOW_IMAGE_URI \
--set images.proxyagent=$MLFLOW_PROXY_URI \
--set defaultArtifactRoot=$GCS_BUCKET_NAME/experiments \
--set backendStore.mysql.host="127.0.0.1" \
--set backendStore.mysql.port="3306" \
--set backendStore.mysql.database="mlflow" \
--set backendStore.mysql.username=$SQL_USERNAME \
--set backendStore.mysql.password=$SQL_PASSWORD \
--set cloudSqlConnection.name=$MLFLOW_SQL_CONNECTION_NAME \
mlflow-helm

# Generate command for debug:
#echo Template command
#echo helm template mlflow --namespace mlflow --set images.mlflow=$MLFLOW_IMAGE_URI --set images.proxyagent=$MLFLOW_PROXY_URI --set defaultArtifactRoot=$GCS_BUCKET_NAME/experiments --set backendStore.mysql.host="127.0.0.1" --set backendStore.mysql.port="3306" --set backendStore.mysql.database="mlflow" --set backendStore.mysql.user=$SQL_USERNAME --set backendStore.mysql.password=$SQL_PASSWORD --set cloudSqlConnection.name=$MLFLOW_SQL_CONNECTION_NAME --output-dir './yamls' mlflow-helm

echo "MLflow Tracking server provisioned."
echo

echo Build customized common ML docker image for AI Platform

NB_IMAGE_URI="gcr.io/$PROJECT_ID/$DEPLOYMENT_NAME-mlimage:latest"
gcloud builds submit custom-notebook --timeout 15m --tag ${NB_IMAGE_URI}

# Note: MLflow provisioning takes minutes. After the mlimage creation it should be available.
MLFLOW_SQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUD_SQL --format="value(connectionName)")
MLFLOW_SQL_CONNECTION_STR="mysql+pymysql://$SQL_USERNAME:$SQL_PASSWORD@127.0.0.1:3306/mlflow"
MLFLOW_TRACKING_EXTERNAL_URI="https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
MLFLOW_URI_FOR_COMPOSER="http://"$(kubectl get svc -n mlflow mlflow -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].port}')

# Add MLflow URI to Cloud Composer as environment variable
echo "Add MLflow URI to Cloud Composer as environment variable..."
gcloud composer environments update $COMPOSER_NAME \
  --update-env-variables=MLFLOW_TRACKING_URI=$MLFLOW_URI_FOR_COMPOSER \
  --location=$REGION \
  --async
echo

# Create connection info which will be used as environment variables inside the Notebook instance.
cat > custom-notebook/notebook-env.txt << EOF
MLFLOW_SQL_CONNECTION_STR=${MLFLOW_SQL_CONNECTION_STR}
MLFLOW_SQL_CONNECTION_NAME=${MLFLOW_SQL_CONNECTION_NAME}
MLFLOW_EXPERIMENTS_URI=${GCS_BUCKET_NAME}/experiments
MLFLOW_TRACKING_URI=http://127.0.0.1:80
MLFLOW_TRACKING_EXTERNAL_URI=${MLFLOW_TRACKING_EXTERNAL_URI}
MLOPS_COMPOSER_NAME=${COMPOSER_NAME}
MLOPS_REGION=${REGION}
EOF

gsutil cp custom-notebook/notebook-env.txt $GCS_BUCKET_NAME
rm custom-notebook/notebook-env.txt

tput setaf 3;
echo MLflow UI can be accessed externally at the below URI:
echo $MLFLOW_TRACKING_EXTERNAL_URI
tput setaf 7;

echo "Enviornment is provisioned successfully."
