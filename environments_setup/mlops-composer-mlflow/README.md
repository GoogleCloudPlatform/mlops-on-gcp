# Setting up an MLOps Environment with Cloud Composer and MLflow on Google Cloud

We describe how to provision and MLOps environment using [Cloud Composer](https://cloud.google.com/composer)
and [MLflow](https://mlflow.org/) on Google Cloud. This environment enables deploying and executing
ML continuous training pipelines, as well as managing and tracking ML experiments, metadata, and artifacts.

We assume that you already have a [GCP Project](https://cloud.google.com/cloud-resource-manager), with 
[billing enabled](https://cloud.google.com/billing/docs/how-to/modify-project). You will also need
[Project Editor](https://cloud.google.com/iam/docs/understanding-roles) permission to provision this environment.

## Environment overview

The proposed MLOps environment consists of the following components:

| Component         | Description |
|-----------------|-------------|
|[AI Platform Notebooks](https://cloud.google.com/ai-platform-notebooks) | A managed JupyterLab instances for ML experimentation. The instance uses a custom container with MLflow installed and Cloud Proxy to connect to Cloud SQL
|[Cloud Composer](https://cloud.google.com/composer) | A managed [Airflow](https://airflow.apache.org/) service to deploy, schedule, and orchestration  run ML training pipelines. It runs on [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine).
|[MLflow](https://mlflow.org/) | An open source platform for managing the ML ifecycle.  In this environment, MLflow used for tracking ML metadata and artifacts.
|[Cloud SQL](https://cloud.google.com/sql/docs) | A managed relational database service. In this environment, Cloud SQL used as a backend for the [MLFlow tracking](https://www.mlflow.org/docs/latest/tracking.html#tracking).
|[Cloud Storage](https://cloud.google.com/storage) | A simple, reliable, and highly-durable object store. In this environment, Cloud Storage is used as an artifact store, where the outputs of ML pipeline steps are saved.
|[Cloud Build](https://cloud.google.com/cloud-build)| A managed service for executing CI/CD routines on Google Cloud infrastructure. In this environment, Cloud Build is used to build the AI Notebooks instance custom container image, as well as  ML model training runtimes.
|[Container Registry](https://cloud.google.com/container-registry)| A single place for a team to store and manage Docker images. In this environment, Container Registry is used to store the container images that are produced by Cloud Build.

## Installation Script

Provisioning of the environment has been automated with the [install.sh](install.sh) script.

The following tables describes the parameters required for the installation:

| Parameter       | Optional | Default       | Description                                                                                                                       |
|-----------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------|
| PROJECT_ID      | Required |               | The project id of your GCP project                                                                                                    |
| SQL_PASSWORD    | Required |               | The password for the Cloud SQL root user                                                                                          |
| DEPLOYMENT_NAME | Optional | mlops         | Short name prefix of infrastructure element and folder names                                                                      |
| REGION          | Optional | us-central1   | A GCP region across the globe. Best to select one of the nearest.                                                                 |
| ZONE            | Optional | us-central1-a | A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones' |


The installation script performs the following steps:

1. Enables necessary APIs
2. Creates a Cloud Storage bucket as an artifact store
3. Creates Cloud SQL instance
4. Provisions a Composer cluster environment in GKE
5. Deploys MLflow server to Composer GKE cluster
6. Create a AI Platform Notebooks instance using a custom image.

### 1. Enable the required APIs

In addition to the [services enabled by default](https://cloud.google.com/service-usage/docs/enabled-service), the following additional services must be enabled

- Compute Engine
- Container Registry
- Cloud Build
- Cloud Composer


### 2. Create a Cloud Storage bucket

A Cloud Storage bucket is required as an ML **artifact store**. The artifacts produced by the various ML steps, such as 
data splits, trained models, evaluation metrics, will be saved in this bucket.

The Cloud Storage bucket name will be set to **<DEPLOYMENT_NAME>-artifact-store**.

### 3. Provisioning a Cloud SQL instance

A Cloud SQL instance is used as a the MLflow backend to store ML metadata and pointers to artifacts stored
in the Cloud Storage bucket.

The Cloud SQL instance name will be set to **<DEPLOYMENT_NAME>-sql**, and the **root** user password will be set to <SQL_PASSWORD>.
A database named **mlflow** will be created in the Cloud SQL instance.

For more information, see [Cloud SQL setup and available machine types](https://cloud.google.com/sql/docs/mysql/create-instance#gcloud>).


### 4. Provisioning Cloud Composer

Cloud Composer will run ML training pipelines, implemented in  Airflow, on a managed environment.
Cloud Composer installation created a GKE cluster in the `REGION` and `ZONE` provided.

The Cloud Composer cluster name will be set to **<DEPLOYMENT_NAME>-af**

By default, the `--machine-type` is set to `n1-standard-2`, `--node-count` is set to 3, and `--python-version` is set to 3.

After the Cloud Composer is provisioned, Python packages in the [requirements.txt](requirements.txt) file are installed
to the Composer runtime. The file includes MLflow, SciPy, and Scikit-learn. You can add other libraries (e.g. TensorFlow or PyTorch)
if your ML pipelines uses them.

For more information, see [Creating environments](https://cloud.google.com/composer/docs/how-to/managing/creating)
in the Cloud Composer documentation.


### 5. Deploying MLflow server to Composer GKE cluster

We deploy and run MLflow as a pod to the Composer GKE cluster, using the following steps:

1. MLflow server will need to connect to the Cloud SQL to store the ML metadata.
The connection will be possible via a [Cloud SQL Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy).
Therefore, we create a service account `sql-proxy-access@PROJECT_ID.iam.gserviceaccount.com`, 
and download the account key to `sql-access.json` file. This will be used by the Cloud Proxy. 
The service account is granted `cloudsql.client` IAM role.

2. Docker container image with MLflow installed is created and pushed to Container Registry.
The container image uses this [Dockerfile](mlflow-helm/docker/Dockerfile), where `mlflow server` 
command is the entry point.

3. we use [Helm](https://helm.sh/) to deploy the MLflow container to the GKE cluster.
Helm compiles Kubernetes application configuration and deploys all components to the cluster. 
The helm configurations for the our MLflow server installation are found in [mlflow-helm](mlflow-helm).


## Running the installation script

You will run the provisioning script using [Cloud Shell](https://cloud.google.com/shell/docs/launching-cloud-shell).

To start the provisioning script:

1. Open **Cloud Shell**
2. Clone this repo under your home folder.

   ```
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    cd mlops-on-gcp/environments_setup/mlops-composer-mlflow
   ```
3. Install [Helm](https://helm.sh/) to Cloud Shell
    ```
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
    ```
4. Start installation
    ```
    ./install.sh [PROJECT_ID] [SQL_PASSWORD] [DEPLOYMENT_NAME] [REGION] [ZONE]
    ```

The `install.sh` script has default parameters for `DEPLOYMENT_NAME`, `REGION` and `ZONE`. 
You must provide `PROJECT_ID` and `SQL_PASSWORD`. 

Executing the script takes around 30 minutes. At the end of execution MLflow URL will be printed to console after 'MLflow UI 
can be accessed at the below URI' message.


## Creating AI Platform Notebooks Instance

The AI Platform Notebooks instance will be your interface of the development environment to define and save experimentation code.
Your notebooks and code files will be saved to your source repository.

Your instance  will need to use MLflow, which uses the same Cloud SQL instance used by the Cloud Composer 
environment as a backend. Therefore, your instance will need to Mlflow installed, and access to the Cloud SQL 
instance via Cloud Proxy. 

We use a [custom Docker container image](custom-notebook) for the AI Notebooks instance with the required
setup and libraries. 

To create the AI Notebooks instance with the custom container, first you need to set `PROJECT_ID`, `NOTEBOOK_NAME` 
and `$ZONE` environment variables, and perform the following steps:

1. Build container

    ```bash
    NB_IMAGE_URI="gcr.io/${PROJECT_ID}/${NOTEBOOK_NAME}-image:latest"

    gcloud builds submit custom-notebook --timeout 15m --tag ${NB_IMAGE_URI}
    ```

    The build steps take around 5 minutes... 

2. Provision a new AI Notebooks instance from using the custom Docker container image

    ```bash
    gcloud compute instances create $NOTEBOOK_NAME \
    --zone=$ZONE \
    --image-family=common-container \
    --machine-type=n1-standard-4 \
    --image-project=deeplearning-platform-release \
    --maintenance-policy=TERMINATE \
    --boot-disk-device-name=${NOTEBOOK_NAME}-disk \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --scopes=cloud-platform,userinfo-email \
    --metadata="proxy-mode=service_account,container=$NB_IMAGE_URI"
    ```

    The AI Notebooks instance will be created in 2-5 minutes.
    
The instance will be in the [AI Platform Notebooks list](https://console.google.com/ai-platform/notebooks/instances). 
You can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the **OPEN JUPYTERLAB** link.

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


## Uninstall the environment

Run the [destroy.sh](destroy.sh) script to turn down the services you provisioned:
```
./destroy.sh [PROJECT_ID] [DEPLOYMENT_NAME] [REGION] [ZONE] 
```
