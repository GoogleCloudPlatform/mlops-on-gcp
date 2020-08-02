# Setting up an MLOps Environment with Cloud Composer and MLflow on Google Cloud

We describe how to provision an MLOps environment using [Cloud Composer](https://cloud.google.com/composer)
and [MLflow](https://mlflow.org/) on Google Cloud. This environment enables deploying and executing
ML continuous training pipelines, as well as managing and tracking ML experiments, metadata, and artifacts.

## Environment overview

The diagram shows the overall MLOps environment

![architecture](../../images/mlops-composer-mlflow.png)

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

## Before you begin

In the following steps we assume that you already have a [GCP Project](https://cloud.google.com/cloud-resource-manager), with
[billing enabled](https://cloud.google.com/billing/docs/how-to/modify-project). You will also need
[Project Editor](https://cloud.google.com/iam/docs/understanding-roles) permission to provision this environment.

For the sake of simplicity, you need to have Project Owner permission in your GCP project to setup this environment. Because of the complexity of this solution, we recommend creating a new isolated GCP project for testing this idea and at the end you can delete all resources allocated during the following steps. Also, before starting the setup environment you should decide where you want to locate all resources

## Installation Script

Provisioning of the environment has been automated with the [install.sh](install.sh) script.
The installation script performs the following steps:

1. Enables necessary APIs
2. Creates a Cloud Storage bucket as an artifact store
3. Creates Cloud SQL instance
4. Provisions a Composer cluster environment in GKE
5. Deploys MLflow server to Composer GKE cluster

### 1. Enable the required APIs

In addition to the [services enabled by default](https://cloud.google.com/service-usage/docs/enabled-service), the following additional services must be enabled

- Compute Engine
- Container Registry
- Cloud Build
- Cloud Composer
- Dataflow
- SQL Admin
- Notebooks

### 2. Create a Cloud Storage bucket

A Cloud Storage bucket is required as an ML **artifact store**. The artifacts produced by the various ML steps, such as 
data splits, trained models, evaluation metrics, will be saved in this bucket.

The Cloud Storage bucket name will be set to **<DEPLOYMENT_NAME>-artifacts**.

### 3. Provisioning a Cloud SQL instance

A Cloud SQL instance is used as an MLflow backend to store ML metadata and pointers to artifacts stored
in the Cloud Storage bucket.

The Cloud SQL instance name will be set to **<DEPLOYMENT_NAME>-sql**, and the default **root** user password will be set to <SQL_PASSWORD>.
A database named **mlflow** will be created in the Cloud SQL, MySQL instance.

For more information, see [Cloud SQL setup](https://cloud.google.com/sql/docs/mysql>) and about user and security management,
see [Creating and managing MySQL users](https://cloud.google.com/sql/docs/mysql/create-manage-users).


### 4. Provisioning Cloud Composer

Cloud Composer will run ML training pipelines, implemented in Airflow, on a managed environment.
Cloud Composer installation created a GKE cluster in the `REGION` and `ZONE` provided.

The Cloud Composer cluster name will be set to **<DEPLOYMENT_NAME>-af**

By default, the `--machine-type` is set to `n1-standard-2`, `--node-count` is set to 3, and `--python-version` is set to 3.

After the Cloud Composer is provisioned, Python packages in the [composer-requirements.txt](composer-requirements.txt) file are installed
to the Composer runtime. The file includes MLflow, SciPy, and Scikit-learn. For more information,
see [Creating environments](https://cloud.google.com/composer/docs/how-to/managing/creating) in the Cloud Composer documentation.

> Note that the ML steps like data pre-processing and model training and evaluation, where large compute
> resources are required advised to
> to execute in their appropriate GCP managed services(e.g. Dataflow and AI Platform),
> rather than in the Composer runtime. However, some small steps might be executed with the Composer runtime,
> like comparing evaluation metrics and logging information to MLflow tracking. Thus, some libraries need
> to be installed in the Composer runtime.
---


### 5. Deploying MLflow server to Composer GKE cluster

Script deploys and runs MLflow as a pod to the Composer GKE cluster, using the following steps:

1. MLflow server will need to connect to the Cloud SQL to store the ML metadata.
The connection will be possible via a [Cloud SQL Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy).
Therefore, script creates a service account `sql-proxy-access@PROJECT_ID.iam.gserviceaccount.com`,
and downloads the account key to `sql-access.json` file.
Key will be used for the [Cloud SQL Proxy authorization](https://cloud.google.com/sql/docs/mysql/authorize-proxy).
The service account is granted a single `cloudsql.client` IAM role, which enables the connection between proxy and
MySQL server, but it does not restrict database level permissions. Database access is managed by general MySQL user name based
authorization.

2. Docker container image with MLflow installed is created and pushed to Container Registry.
The container image uses this [Dockerfile](mlflow-helm/docker/Dockerfile), where `mlflow server`
command is the entry point.
Along with the main MLflow image, a side-car container will be created to be a proxy server to expose
[MLflow Tracking web UI](https://www.mlflow.org/docs/latest/tracking.html#tracking-ui).

3. Script uses [Helm](https://helm.sh/) to deploy the MLflow container to the Composer's GKE cluster.
Helm compiles Kubernetes application configuration and deploys all components.
The helm templates for the MLflow server installation are found in [mlflow-helm](mlflow-helm) folder.

After all image buildings, hosting and SQL connection definitions, the process and the final landscape of interconnections will be this:

![mlflow-connections](../../images/mlops-composer-mlflow-mlflow-connections.png)

> MLflow connections detailed:
> 
> In this MLOps environment we implemented two MLflow Tracking server instances.
> To reduce connection complexities, each instance is available through local connections.
>
> 1. from Notebook through localhost
> 2. from Airflow through K8s cluster internal IP exposed by K8s service.
> 
> Both instances share the same MySQL database in the same Cloud SQL instance, thanks to MLflow Tracking Service stateless operation.
> Instead of accessing SQL server directly we applied SQL proxy between MLFlow and SQL server.
> MLflow tracking server doesn't have internal authentication method or TLS, because of those limitations MLFlow Web interface exposed via
> inverted proxy which available via an hashed URL format, like this: `https://abcdef123456789-dot-us-central1.notebooks.googleusercontent.com/`.
> MLFlow URL will be saved to `MLFLOW_TRACKING_EXTERNAL_URI` env. variable as a result of the provisioning process.

### 6. Build the common ML container image

Services and Jupyter notebook in ML container have access to provisioned infrastructure components such as SQL server and MLflow service.
Connection URIs and other settings are propagated via environment variables. Environment setting for Notebook is build in this method
and stored in file in GCS

   ```
    cat > custom-notebook/notebook-env.txt << EOF
    MLFLOW_SQL_CONNECTION_STR=mysql+pymysql://${SQL_USERNAME}:${SQL_PASSWORD}@127.0.0.1:3306/mlflow
    MLFLOW_SQL_CONNECTION_NAME=$(gcloud sql instances describe ${CLOUD_SQL} --format="value(connectionName)")
    MLFLOW_EXPERIMENTS_URI=${gs://$DEPLOYMENT_NAME-artifacts/experiments}
    MLFLOW_TRACKING_URI=http://127.0.0.1:80
    MLFLOW_TRACKING_EXTERNAL_URI="https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
    MLOPS_COMPOSER_NAME=${DEPLOYMENT_NAME}-af
    MLOPS_REGION=${REGION}
    EOF

    gsutil cp custom-notebook/notebook-env.txt ${gs://$DEPLOYMENT_NAME-artifacts}
    rm custom-notebook/notebook-env.txt
   ```

This file will be referred in Notebook provisioning command parameter:
`--metadata ... container-env-file=$GCS_BUCKET_NAME/notebook-env.txt`

MLflow local service instance connects Cloud SQL service which is defined in [entrypoint.sh](custom-notebook/entrypoint.sh) leveraging these variables.

By convention MLFflow URI will be set from [MLFLOW_TRACKING_URI](https://www.mlflow.org/docs/latest/tracking.html#where-runs-are-recorded)
environment variable, but pointing to the localhost server instance (127.0.0.1).

This common ML container build step is defined in the [custom-notebook](custom-notebook) folder and the build requires around 5 minutes for completion.
   ```
   NB_IMAGE_URI="gcr.io/$PROJECT_ID/$DEPLOYMENT_NAME-mlimage:latest"
   gcloud builds submit custom-notebook --timeout 15m --tag ${NB_IMAGE_URI}
   ```

## Running the installation script

You will run the provisioning script using [Cloud Shell](https://cloud.google.com/shell/docs/launching-cloud-shell).

To start the provisioning script:

1. Open **Cloud Shell**
   Keep Cloud Shell open during the whole provisioning. If you close your Cloud Shell session, you lose the environment variables.
2. Clone this repo under your home folder.

   ```
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    cd mlops-on-gcp/environments_setup/mlops-composer-mlflow
   ```
3. Install and initialize [Helm](https://helm.sh/) to Cloud Shell
    ```
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
   
    helm repo add stable https://kubernetes-charts.storage.googleapis.com/
    helm repo update
    ```
4. Start installation
    ```
    source install.sh [PROJECT_ID] [SQL_PASSWORD] [DEPLOYMENT_NAME] [REGION] [ZONE]
    ```
The following tables describes the parameters required for the installation:

| Parameter       | Optional | Default       | Description                                                                                                                       |
|-----------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------|
| PROJECT_ID      | Required |               | The project id of your GCP project                                                                                                    |
| SQL_PASSWORD    | Required |               | The password for the Cloud SQL root user                                                                                          |
| DEPLOYMENT_NAME | Optional | mlops         | Short name prefix of infrastructure element and folder names. Default: mlflow                                                                      |
| REGION          | Optional | us-central1   | A GCP region across the globe. Best to select one of the nearest. Default: us-central-1                                                                |
| ZONE            | Optional | us-central1-a | A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones'. Default: us-central1-a |

Script  calls [set-env-var.sh](set-env-var.sh) to setup environment variables, that will be required for AI Platform Notebook provisioning step.

The `install.sh` script has default parameters for `DEPLOYMENT_NAME`, `REGION` and `ZONE`.
You must provide `PROJECT_ID` and `SQL_PASSWORD`.

Executing the script takes around 30 minutes.

> Please, note:
> 1. At the end of process, MLflow URL will be printed to the console after the
   'MLflow UI can be accessed at the below URI:' message.
> 2. MLFLOW_TRACKING_EXTERNAL_URI variable will be set to MLflow URL in Cloud Shell.
> 3. MLFLOW_TRACKING_EXTERNAL_URI will be available in Notebook Terminal as well.


## Creating AI Platform Notebooks Instance

The AI Platform Notebooks instance will be your interface of the development environment to define and save experimentation code.
Your notebooks and code files will be saved to Notebook local instance which is a stateless Docker container, therefore please use
[integrated Git to save your experiments](https://cloud.google.com/ai-platform/notebooks/docs/save-to-github).

Your Notebook instance will need to use a local MLflow server, which connects to the same Cloud SQL instance that is used by the previously provisioned
and dedicated MLflow instance (5th step).

We use the custom ML image created saved to Cloud Repository ($NB_IMAGE_URI) in the previous 6th step for the AI Notebooks instance. Image contains all required
setup and libraries.

This command provisions a new AI Notebooks instance.

   ```
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
   ```

AI Notebooks instance will be created in 2-5 minutes. Required variables already set. If you need to redeploy Notebook
with different parameters later, might call `set-env-vars.sh` before.

The instance will be in the [AI Platform Notebooks list](https://console.google.com/ai-platform/notebooks/instances).
You can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the **OPEN JUPYTERLAB** link.

> Please note that this method is very custom and based on Beta features, might change in the near future.
> For more details and about Notebook customization parameters,
> see [Using a custom container](https://cloud.google.com/ai-platform/notebooks/docs/custom-container)

## Verifying the Infrastructure

1. Open the JupyterLab in the AI Notebook instance

2. Clone Github repository
    ```bash
    cd /home/jupyter
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    ```

3. Open 'environment-test.ipynb' Notebook under `mlops-on-gcp/environments_setup/mlops-composer-mlflow` directory.
Select 'Run'->'Run All Cells'. The Notebook trains a simple logistic regression while sending logs to MLflow.

4. Open MLflow UI and check new logs of environment-test execution should appear. Notebook UI URL available in

   a. Notebook terminal

    ```bash
   echo $MLFLOW_TRACKING_EXTERNAL_URI
    ```

   b. Cloud Shell
    ```bash
    echo "https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
    ```

![MLflow logs](../../images/mlflow-env-test.png)


## Uninstall and clean up the environment

Run the [destroy.sh](destroy.sh) script to turn down the services you provisioned:
```
./destroy.sh [PROJECT_ID] [DEPLOYMENT_NAME] [REGION] [ZONE]
```

This destroy script won't turn-down the AI Platform Notebook instance and won't clear IAM service account and key. You need to delete them manually.
