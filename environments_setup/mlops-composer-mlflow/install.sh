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

if [[ -z "${PROJECT_ID}" ]]; then
  echo PROJECT_ID is not set
  exit 1
fi

if [[ -z "${SQL_USERNAME}" ]]; then
  echo SQL_USERNAME is not set
  exit 1
fi

if [[ -z "${SQL_PASSWORD}" ]]; then
  echo SQL_PASSWORD is not set
  exit 1
fi

if [[ -z "${DEPLOYMENT_NAME}" ]]; then
  echo DEPLOYMENT_NAME is not set
  exit 1
fi

if [[ -z "${REGION}" ]]; then
  echo REGION is not set
  exit 1
fi

if [[ -z "${ZONE}" ]]; then
  echo ZONE is not set
  exit 1
fi

if [[ -z "${GCS_BUCKET_NAME}" ]]; then
  echo GCS_BUCKET_NAME is not set
  exit 1
fi

if [[ -z "${ML_IMAGE_URI}" ]]; then
  echo ML_IMAGE_URI is not set
  exit 1
fi

trap 'err_handler "$LINENO" "$BASH_COMMAND" "$?"' ERR

tput setaf 3; echo Creating environment
echo Setup started at:
date
tput setaf 7

# Set calculated infrastucture names
CLOUD_SQL="$DEPLOYMENT_NAME-sql"
COMPOSER_NAME="$DEPLOYMENT_NAME-af"
MLFLOW_IMAGE_URI="gcr.io/${PROJECT_ID}/$DEPLOYMENT_NAME-mlflow"
MLFLOW_PROXY_URI="gcr.io/${PROJECT_ID}/inverted-proxy"

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

#2. Create a Cloud Storage bucket

echo "Creating GCS bucket for artifacts..."
if ! gsutil list "$GCS_BUCKET_NAME"; then
gsutil mb -p $PROJECT_ID -l $REGION $GCS_BUCKET_NAME
fi
echo "GCS bucket available: $GCS_BUCKET_NAME"
echo

# 3. Provisioning a Cloud SQL instance

if [[ $(gcloud sql instances list --filter="$CLOUD_SQL" --format='value(name)') != "$CLOUD_SQL" ]]; then
    echo "Provisioning Cloud SQL..."
    gcloud sql instances create $CLOUD_SQL --tier=db-g1-small --region=$REGION
    gcloud sql databases create mlflow --instance=$CLOUD_SQL
    gcloud sql users set-password $SQL_USERNAME --host=% --instance=$CLOUD_SQL --password=$SQL_PASSWORD
fi
MLFLOW_SQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUD_SQL --format="value(connectionName)")
echo "Cloud SQL is available: $MLFLOW_SQL_CONNECTION_NAME"

# 4. Provisioning Cloud Composer

# Creating Cloud Composer
if [[ $(gcloud composer environments list --locations=$REGION --filter="$COMPOSER_NAME" --format='value(name)') != "$COMPOSER_NAME" ]]; then
    echo "Provisioing Cloud Composer..."
    gcloud composer environments create $COMPOSER_NAME \
    --location=$REGION \
    --zone=$ZONE \
    --airflow-configs=core-dags_are_paused_at_creation=True \
    --disk-size=50GB \
    --image-version=composer-1.13.4-airflow-1.10.12 \
    --machine-type=n1-standard-2 \
    --node-count=3 \
    --python-version=3 \
    --enable-ip-alias

# Installing Python packages to Composer
  echo "Install Python packages to Cloud Composer..."
  gcloud composer environments update $COMPOSER_NAME \
    --update-pypi-packages-from-file=composer-requirements.txt \
    --location=$REGION
fi
echo "Cloud Composer is available: $COMPOSER_NAME"
echo


# 5. Deploying MLflow server to Composer GKE cluster

echo "Provisioning MLflow Tracking server..."

# Set local Kubernetes configuration to connect to Composer GKE cluster
echo "Setting configuration to connect to Composer GKE cluster..."
# 'goog-composer-environment' label is set to $COMPOSER_NAME
GKE_CLUSTER=$(gcloud container clusters list --limit=1 --zone=$ZONE --filter="resourceLabels.goog-composer-environment=$COMPOSER_NAME" --format="value(name)")
gcloud container clusters get-credentials $GKE_CLUSTER --zone $ZONE --project $PROJECT_ID

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
    cp mlflow-helm/sql-access.json custom-ml-image/
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
kubectl create namespace mlflow || echo "'mlflow' namespace already exists"

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
#echo helm template mlflow --namespace mlflow --set images.mlflow=$MLFLOW_IMAGE_URI --set images.proxyagent=$MLFLOW_PROXY_URI --set defaultArtifactRoot=$GCS_BUCKET_NAME/experiments --set backendStore.mysql.host="127.0.0.1" --set backendStore.mysql.port="3306" --set backendStore.mysql.database="mlflow" --set backendStore.mysql.user=$SQL_USERNAME --set backendStore.mysql.password=$SQL_PASSWORD --set cloudSqlConnection.name=$MLFLOW_SQL_CONNECTION_NAME --output-dir './yamls' mlflow-helm

MLFLOW_SQL_CONNECTION_STR="mysql+pymysql://$SQL_USERNAME:$SQL_PASSWORD@127.0.0.1:3306/mlflow"

echo "Waiting for MLflow Tracking server provisioned"

# External URL to Mlflow
MLFLOW_TRACKING_EXTERNAL_URI="https://"
# Internal access from Composer to Mlflow
MLFLOW_URI_FOR_COMPOSER=="http://"
while [ "$MLFLOW_TRACKING_EXTERNAL_URI" == "https://" ] || [ "$MLFLOW_URI_FOR_COMPOSER" == "http://" ]
do
  echo "wait 5 seconds..."
  sleep 5s
  MLFLOW_TRACKING_EXTERNAL_URI="https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
  MLFLOW_URI_FOR_COMPOSER="http://"$(kubectl get svc -n mlflow mlflow -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].port}')
done

echo "MLflow Tracking server provisioned"
echo
echo 6. Build the common ML container image

# init.sh will be executed durring trainer image containerization
cat > custom-ml-image/init.sh << EOF
#!/bin/bash
export MLFLOW_GCS_ROOT_URI=${GCS_BUCKET_NAME}
export MLFLOW_SQL_CONNECTION_STR=${MLFLOW_SQL_CONNECTION_STR}
export MLFLOW_SQL_CONNECTION_NAME=${MLFLOW_SQL_CONNECTION_NAME}
export MLFLOW_EXPERIMENTS_URI=${GCS_BUCKET_NAME}/experiments
export MLFLOW_TRACKING_URI=http://127.0.0.1:80
export MLFLOW_TRACKING_EXTERNAL_URI=${MLFLOW_TRACKING_EXTERNAL_URI}
export MLOPS_COMPOSER_NAME=${COMPOSER_NAME}
export MLOPS_REGION=${REGION}
export ML_IMAGE_URI=${ML_IMAGE_URI}

/usr/local/bin/cloud_sql_proxy -dir=/var/run/cloud-sql-proxy -instances=${MLFLOW_SQL_CONNECTION_NAME}=tcp:3306 -credential_file=/usr/local/bin/sql-access.json &
sleep 5s
mlflow server --host=127.0.0.1 --port=80 --backend-store-uri=${MLFLOW_SQL_CONNECTION_STR} --default-artifact-root=${GCS_BUCKET_NAME}/experiments &
EOF

# Custom ML image URI needed for projecting a new trainer job from Notebooks or Airflow 
gcloud builds submit custom-ml-image --timeout 15m --tag ${ML_IMAGE_URI}

# Note: MLflow provisioning takes minutes. After the mlimage creation it should be available.

# Add MLflow URI to Cloud Composer as environment variable
echo "Add MLflow URI to Cloud Composer as environment variable..."
gcloud composer environments update $COMPOSER_NAME \
  --update-env-variables MLFLOW_TRACKING_URI=$MLFLOW_URI_FOR_COMPOSER,MLFLOW_GCS_ROOT_URI=$GCS_BUCKET_NAME \
  --location $REGION \
  --async
echo

# Create connection info which will be used as environment variables inside the Notebook instance.
cat > custom-ml-image/notebook-env.txt << EOF
MLFLOW_GCS_ROOT_URI=${GCS_BUCKET_NAME}
MLFLOW_SQL_CONNECTION_STR=${MLFLOW_SQL_CONNECTION_STR}
MLFLOW_SQL_CONNECTION_NAME=${MLFLOW_SQL_CONNECTION_NAME}
MLFLOW_EXPERIMENTS_URI=${GCS_BUCKET_NAME}/experiments
MLFLOW_TRACKING_URI=http://127.0.0.1:80
MLFLOW_TRACKING_EXTERNAL_URI=${MLFLOW_TRACKING_EXTERNAL_URI}
MLOPS_COMPOSER_NAME=${COMPOSER_NAME}
MLOPS_REGION=${REGION}
ML_IMAGE_URI=${ML_IMAGE_URI}
EOF

gsutil cp custom-ml-image/notebook-env.txt $GCS_BUCKET_NAME
rm custom-ml-image/notebook-env.txt
tput setaf 3;
echo "MLflow UI can be accessed externally at the below URI:"
echo $MLFLOW_TRACKING_EXTERNAL_URI
tput setaf 7;

echo "Enviornment is provisioned successfully."
