# Setting up an MLOps Enviroment with Cloud Composer and MLflow on Google Cloud

Before you begin

For the sake of simplicity, you need to have Project Owner permission in your GCP project to setup this environment. Because of the complexity of this solution, we recommend creating a new dedicated GCP project for testing this idea and at the end you can delete all resources allocated during the following steps. Also, you should decide where do you want to locate all resources. To make following setup consistent, you should set these environment variables that will be used in many scripts later.

## Automated install by script

Simply launch [Cloud Shell](https://cloud.google.com/shell/docs/launching-cloud-shell) and keep it open.

Provisioning of the environment has been automated with the *install.sh* script.
The script goes through the following steps, but if you prefer you can [go trough 
manually over each steps](#manual-environment-setup) without executing *install.sh* script.

1. Enables necessary APIs
2. Creates Cloud SQL instance
3. Provisions a Composer cluster environment in GKE
4. Builds a MLflow docker image and deploy it to Composer cluster
5. Builds a custom Notebook image and create a AI Platform Notebooks instance from the image. 

So, the first step to clone repository files and execute script:

    ```bash
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    cd mlops-on-gcp/environments_setup/mlops-composer-mlflow

    ./install.sh \ 
    PROJECT_ID \
    SQL_PASSWORD \
    DEPLOYMENT_NAME \
    REGION \
    ZONE \
    ```

install.sh script has default parameters for DEPLOYMENT_NAME, REGION and ZONE, you must provide PROJECT_ID and SQL_PASSWORD.

| Parameter       | Optional | Default       | Description                                                                                                                       |
|-----------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------|
| PROJECT_ID      | Required |               | The project id of your project                                                                                                    |
| SQL_PASSWORD    | Required |               | The password for the Cloud SQL root user                                                                                          |
| DEPLOYMENT_NAME | Optional | mlops         | Short name prefix of infrastructure element and folder names                                                                      |
| REGION          | Optional | us-central1   | A GCP region across the globe. Best to select one of the nearest.                                                                 |
| ZONE            | Optional | us-central1-a | A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones' |

Executing the script takes around 30 minutes. At the end of execution MLflow URL will be printed to console after 'MLflow UI 
can be accessed at the below URI' message.

To test environment just [jump to to 'Verifying the infrastucture' section](#verifying-the-infrastructure)

Run the *destroy.sh* script to turn down the services you provisioned.

    ```bash
    ./destroy.sh PROJECT_ID DEPLOYMENT_NAME [REGION] [ZONE] 
    ```

## Manual environment setup


### Set your project ID, region and zone

    ```bash
    gcloud config set project [YOUR GCP PROJECT NAME]
    PROJECT_ID=$(gcloud config list --format 'value(core.project)')
    REGION=[YOUR REGION]
    ZONE=[YOUR ZONE]
    DEPLOYMENT_NAME=[SHORT NAME OF DEPLOYMENT]

    CLOUD_SQL="$DEPLOYMENT_NAME-sql"
    COMPOSER_NAME="$DEPLOYMENT_NAME-af"
    NOTEBOOK_NAME="$DEPLOYMENT_NAME-nb"
    GCS_BUCKET_NAME="$DEPLOYMENT_NAME-mlflow"
    ```

- ’YOUR REGION’ A region across the globe. Best to select one of the nearest. Services in some cases refer to a region by ‘Location’ name. See: [Available Regions and Zones](https://cloud.google.com/compute/docs/regions-zones).
- ’YOUR ZONE’ A zone is an isolated location within a region.

### Enable the required APIs

In addition to the [services enabled by default](https://cloud.google.com/service-usage/docs/enabled-service), the following additional services must be enabled

- Compute Engine
- Container Registry
- Cloud Build
- Cloud Composer
- Cloud Source Repositories

Use [GCP Console](https://console.cloud.google.com/) or gcloud command line interface in Cloud Shell to [enable the required services](https://cloud.google.com/service-usage/docs/enable-disable). The most simplified way to enable all services in a single gcloud command. To enable Cloud Services utilized in the environment:

Use gcloud to enable the services (takes 1-2 minutes)

```bash
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
```

### Provisioning Cloud SQL

```bash
CLOUD_SQL=[YOUR SQL INSTANCE NAME]
SQL_PASSWORD=[PASSWORD FOR ROOT]
SQL_USERNAME=root
gcloud sql instances create $CLOUD_SQL --tier=db-g1-small --region=$REGION
gcloud sql databases create mlflow --instance=$CLOUD_SQL
gcloud sql users set-password $SQL_USERNAME \
    --host=% --instance=$CLOUD_SQL --password=$SQL_PASSWORD
CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUD_SQL --format="value(connectionName)")
```

Suggested machine type tier names:

Tier name (--tier parameter) | Memory | Maximum storage capacity
--- | --- | ---
db-f1-micro | 614.4 MiB | 3.0TiB
db-g1-small | 1.7 GiB | 3.0TiB
db-n1-standard-1 | 3.8GiB | 30TiB

More details about Cloud SQL setup and available machine types:
<https://cloud.google.com/sql/docs/mysql/create-instance#gcloud>

### Provisioing Cloud Composer

At this point Cloud Composer API is already enabled and ready to use for detailed setup. In the following steps you can provision a new Cloud Composer environment from a script. If you prefer to create an environment from the UI here is a [code lab](https://codelabs.developers.google.com/codelabs/intro-cloud-composer/index.html) that guides you through the process.

```bash

gcloud composer environments create $COMPOSER_NAME \
--location=$REGION \
--zone=$ZONE \
--airflow-configs=core-dags_are_paused_at_creation=True \
--disk-size=20GB \
--image-version=composer-1.10.4-airflow-1.10.3 \
--machine-type=n1-standard-2 \
--node-count=3 \
--python-version=3
```

Composer/Airflow provisioning takes around 5-10 minutes. You can check the progress on the Console as well: <https://console.cloud.google.com/composer/environments>

### Provisioning MLflow Server

1. Connect to GKE

    Set local Kubernetes configuration to connect to Composer cluster. See the Google Kubernetes Engine (GKE) guide to [configuring cluster access for kubectl](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)

    ```bash
    GKE_CLUSTER=$(gcloud container clusters list --limit=1 --zone=$ZONE --filter="name~$COMPOSER_NAME" --format="value(name)")
    gcloud container clusters get-credentials --zone $ZONE $GKE_CLUSTER
    ```

2. Create a Kubernetes secret for SQL proxy

    ```bash
    SA_EMAIL=$(gcloud iam service-accounts create sql-proxy-access --format='value(email)' --display-name=sql-proxy-access)
    gcloud iam service-accounts keys create mlflow-helm/sql-access.json --iam-account=$SA_EMAIL

    gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member serviceAccount:$SA_EMAIL \
    --role roles/cloudsql.client
    ```

3. Install Helm chart

    Helm compiles complex Kubernetes application configuration and deploys all components to the cluster. There are various ways to install Helm, see [official documentation](https://helm.sh/docs/intro/install/). One of the most simple ways to install with a script and deploy and init Helm.

    ```bash
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh

    helm repo add stable https://kubernetes-charts.storage.googleapis.com/
    helm repo update

    kubectl create serviceaccount --namespace kube-system tiller
    kubectl create clusterrolebinding tiller-cluster-rule --clusterrole=cluster-admin --serviceaccount=kube-system:tiller
    kubectl patch deploy --namespace kube-system tiller-deploy -p '{"spec":{"template":{"spec":{"serviceAccount":"tiller"}}}}'
    
    ```
4. Build MLflow docker image

    ```bash
    MLFLOW_IMAGE_URI="gcr.io/${PROJECT_ID}/$DEPLOYMENT_NAME"
    gcloud builds submit mlflow-helm/docker --timeout 15m --tag ${MLFLOW_IMAGE_URI}:latest
    ```

5. Deploy MLflow from Helm configuration

    Start deployment.
    GCS_BUCKET_NAME="$DEPLOYMENT_NAME-mlflow"

    ```bash
    helm install mlflow --create-namespace \
    --set image.repository=$MLFLOW_IMAGE_URI \
    --set defaultArtifactRoot=$GCS_BUCKET_NAME \
    --set backendStore.mysql.host="127.0.0.1" \
    --set backendStore.mysql.port="3306" \
    --set backendStore.mysql.database="mlflow" \
    --set backendStore.mysql.username=$SQL_USERNAME \
    --set backendStore.mysql.password=$SQL_PASSWORD \
    --set cloudSqlInstance.name=$CLOUD_SQL_CONNECTION_NAME \
    mlflow-helm
    ```

    Few minutes later a new mlflow deployment with all configuration will be created. MLflow UI available on simple HTTP address:

    ```bash
    MLFLOW_IP=$(kubectl get ingress mlflow --namespace mlflow -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    MLFLOW_URL="http://${MLFLOW_IP}"
    echo MLflow UI: $MLFLOW_URL
    ```

> Use this command to delete MLflow deployment

```bash
helm del mlflow
```

### Creating AI Platform Notebook Instance

Notebook will be your interface of the development environment to define and save experimentation code.
Notebook content will be saved to Cloud Source Repository.
Since AI Platform Notebook is just a VM you can define a ready-to-use notebook with all required libraries by creating a [custom container](https://cloud.google.com/ai-platform/notebooks/docs/custom-container). In the following steps you create a customized notebook Docker image with all required Python libraries and create a running notebook instance. At the end, this notebook will be connected to the Source repository.

1. Base scripts and Dockerfile are located in the ‘notebook’ folder in solution GitHub.

2. Build container

    ```bash
    NB_IMAGE_URI="gcr.io/${PROJECT_ID}/${NOTEBOOK_NAME}-image:latest"

    gcloud builds submit custom-notebook --timeout 15m --tag ${NB_IMAGE_URI}
    ```

    > YOUR-NOTEBOOK-NAME should be short for example: ‘mlops-scikit’

    Build steps take around 5 minutes. At the beginning of the build you will find a log entry in the console that contains an URL for the build process. The format similar to this:

    ...
    Logs are available at [<https://console.cloud.google.com/cloud-build/builds/[GUID]?project=[NUMBER]>]
    ...

3. Provision a new Notebook instance from Docker image

    ```bash
    gcloud compute instances create $NOTEBOOK_NAME \
    --zone=$ZONE \
    --image-family=common-container \
    --machine-type=n1-standard-2 \
    --image-project=deeplearning-platform-release \
    --maintenance-policy=TERMINATE \
    --boot-disk-device-name=${NOTEBOOK_NAME}-disk \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --scopes=cloud-platform,userinfo-email \
    --metadata="proxy-mode=service_account,container=$NB_IMAGE_URI"
    ```

    In this example we choose a small VM instance (n1-standard-2) because the instance is not intended to train ML models or do CPU intensive tasks.

    (alternative way to create manually a custom container on Cloud Console and add additional Python module dependencies is explained in [notebooks documentation](https://cloud.google.com/ai-platform/notebooks/docs/dependencies))

    VM instance will be created and a few minutes (2-5 min) later a new notebook will be available in the [AI Platform Notebooks list](https://console.google.com/ai-platform/notebooks/instances). You can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the OPEN JUPYTERLAB link

## Verifying the Infrastructure

1. Open notebook

    VM instance will be created and a few minutes (2-5 min) later a new notebook will be available in the [AI Platform Notebooks list](https://console.google.com/ai-platform/notebooks/instances). You can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the OPEN JUPYTERLAB link

2. Clone GitHub repo to Notebook to test environment
    There are two GitHub repositories we are using this solution example:
    - your ML-ops CD/CD pipeline workspace. This intermediate read-write repository will be the storage of your experiments in Notebook.
    - One that contains this example codes for the current solution. To test environement you need to clone this repository:

    ```bash
    cd /home
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    ```

    Select 'Git'->'Clone' menu and copy this repository URL and 'Clone' it.

3. Open 'environment-test.ipynb' from the cloned repository 'test' folder.

    environments_setup/mlops-composer-mlflow/test/environment-test.ipynb

Select 'Run'->'Run All Cells' which should execute a simple logistic regression while sending logs to MLflow.

4. Open MLflow UI ($MLFLOW_URL) and check new logs of environment-test execution should be appeared.

    ```bash
    echo "https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
    ```

![MLflow logs](../../images/mlflow-env-test.png)
