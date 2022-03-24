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
|[Cloud SQL](https://cloud.google.com/sql/docs) | A managed relational database service. In this environment, Cloud SQL used as a backend for the [MLflow tracking](https://www.mlflow.org/docs/latest/tracking.html#tracking).
|[Cloud Storage](https://cloud.google.com/storage) | A simple, reliable, and highly-durable object store. In this environment, Cloud Storage is used as an artifact store, where the outputs of ML pipeline steps are saved.
|[Cloud Build](https://cloud.google.com/cloud-build)| A managed service for executing CI/CD routines on Google Cloud infrastructure. In this environment, Cloud Build is used to build the AI Notebooks instance custom container image, as well as  ML model training runtimes.
|[Container Registry](https://cloud.google.com/container-registry)| A single place for a team to store and manage Docker images. In this environment, Container Registry is used to store the container images that are produced by Cloud Build.

In this environment, the MLflow Tracking server is a used in locally in three services.

1. AI Platform Notebook instance(s) - accessed by local Notebooks.
2. Cloud Composer GKE Cluster - accessed by Airflow through K8s cluster internal IP. MLflow is deployed as a pod in the GKE cluster.
3. AI Platform Training - accessed locally by the ML training code.

All the MLflow tracking services share the same backend MySQL database hosted in Cloud SQL, thanks to MLflow Tracking Service stateless operation.
This setup reduces the interconnection complexity.

In addition, [Cloud SQL proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy)
is used to allow MLflow to connect to the Cloud SQL instance.


## Before you begin

In the following steps we assume that you already have a [GCP Project](https://cloud.google.com/cloud-resource-manager), with
[billing enabled](https://cloud.google.com/billing/docs/how-to/modify-project). You will also need
[Project Editor](https://cloud.google.com/iam/docs/understanding-roles) permission to provision this environment.

Update to the latest gcloud command

   ```
   sudo gcloud components update
   ```

## Installation Script

Provisioning of the environment has been automated with the [install.sh](install.sh) script.
The installation script performs the following steps:

1. Enables necessary APIs
2. Creates a Cloud Storage bucket as an artifact store
3. Creates Cloud SQL instance
4. Provisions a Composer cluster environment in GKE
5. Deploys MLflow server to Composer GKE cluster

### 1. Enable the required APIs

In addition to the [services enabled by default](https://cloud.google.com/service-usage/docs/enabled-service), 
the following additional services must be enabled:

- Compute Engine
- Container Registry
- Cloud Build
- Cloud Composer
- Cloud Dataflow
- Cloud SQL Admin
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
> to execute in their appropriate GCP managed services (e.g. Dataflow and AI Platform),
> rather than in the Composer runtime. However, some small steps might be executed with the Composer runtime,
> like comparing evaluation metrics and logging information to MLflow tracking. Thus, some libraries need
> to be installed in the Composer runtime.
---


### 5. Deploying MLflow server to Composer GKE cluster

Deploying and running MLflow as a pod to the Composer GKE cluster requires the following:

1. MLflow server will need to connect to the Cloud SQL to store the ML metadata.
The connection will be possible via a [Cloud SQL Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy).
Therefore, script creates a service account `sql-proxy-access@PROJECT_ID.iam.gserviceaccount.com`,
and downloads the account key to `sql-access.json` file.
Key will be used for the [Cloud SQL Proxy authorization](https://cloud.google.com/sql/docs/mysql/authorize-proxy).
The service account is granted a single `cloudsql.client` IAM role, which enables the connection between proxy and
MySQL server, but it does not restrict database level permissions. Database access is managed by general MySQL user name based
authorization.

2. A Docker container image with MLflow is created and pushed to Container Registry.
The container image uses this [Dockerfile](mlflow-helm/docker/Dockerfile), where `mlflow server`
command is the entry point.
Along with the main MLflow image, a side-car container will be created to be a proxy server to expose
[MLflow Tracking web UI](https://www.mlflow.org/docs/latest/tracking.html#tracking-ui).

3. [Helm](https://helm.sh/) is used to deploy the MLflow container to the Composer's GKE cluster.
Helm compiles Kubernetes application configuration and deploys all components.
The helm templates for the MLflow server installation are found in [mlflow-helm](mlflow-helm) folder.

### 6. Build the common ML container image

Services and Jupyter notebook in ML container have access to provisioned infrastructure components such as 
Cloud SQL and MLflow Tracking service.
Connection URIs and other settings are propagated via environment variables.
Environment setting for the AI Platform Notebooks instance is created and stored 
in file in Cloud Storage, to be used in provisioning an AI Platform Notebooks instance:

   ```
    cat > custom-ml-image/notebook-env.txt << EOF
    MLFLOW_GCS_ROOT_URI=${GCS_BUCKET_NAME}
    MLFLOW_SQL_CONNECTION_STR=mysql+pymysql://${SQL_USERNAME}:${SQL_PASSWORD}@127.0.0.1:3306/mlflow
    MLFLOW_SQL_CONNECTION_NAME=$(gcloud sql instances describe ${CLOUD_SQL} --format="value(connectionName)")
    MLFLOW_EXPERIMENTS_URI=${GCS_BUCKET_NAME}/experiments
    MLFLOW_TRACKING_URI=http://127.0.0.1:80
    MLFLOW_TRACKING_EXTERNAL_URI="https://"$(kubectl describe configmap inverse-proxy-config -n mlflow | grep "googleusercontent.com")
    MLOPS_COMPOSER_NAME=${DEPLOYMENT_NAME}-af
    MLOPS_REGION=${REGION}
    EOF

    gsutil cp custom-ml-image/notebook-env.txt ${gs://$DEPLOYMENT_NAME-artifacts}
    rm custom-ml-image/notebook-env.txt
   ```

MLflow local service instance connects Cloud SQL service which is defined in 'init.sh' leveraging these variables.


This common ML container build step is defined in the [custom-ml-image](custom-ml-image) folder and the build requires around 5 minutes for completion.
   ```
   ML_IMAGE_URI="gcr.io/$PROJECT_ID/$DEPLOYMENT_NAME-mlimage:latest"
   gcloud builds submit custom-ml-image --timeout 15m --tag ${ML_IMAGE_URI}
   ```

## Running the installation script

You will run the provisioning script using [Cloud Shell](https://cloud.google.com/shell/docs/launching-cloud-shell).

To start the provisioning script:

1. Open **Cloud Shell**: Keep Cloud Shell open during the whole provisioning. If you close your Cloud Shell session, you lose the environment variables.
2. Clone this repo under your home folder:

   ```
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    cd mlops-on-gcp/environments_setup/mlops-composer-mlflow
   ```
3. Install and initialize [Helm](https://helm.sh/) to Cloud Shell:
    ```
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
   
    helm repo add stable https://kubernetes-charts.storage.googleapis.com/
    helm repo update
    ```
   
4. Set the environment variables:

    ```
    source set-env-vars.sh [PROJECT_ID] [SQL_PASSWORD] [DEPLOYMENT_NAME] [REGION] [ZONE]
    ```

    The following tables describes the parameters required for the installation, 
    which also will be used for creating the AI Notebook instance:
    
    | Parameter       | Optional | Default       | Description                                                                                                                       |
    |-----------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------|
    | PROJECT_ID      | Required |               | The project id of your GCP project                                                  |
    | SQL_PASSWORD    | Required |               | The password for the Cloud SQL root user                                            |
    | DEPLOYMENT_NAME | Optional | mlops         | Short name prefix of infrastructure element and folder names.                       |
    | REGION          | Optional | us-central1   | A GCP region across the globe. Best to select one of the nearest.                   |
    | ZONE            | Optional | us-central1-a | A zone is an isolated location within a region. Available Regions and Zones: https://cloud.google.com/compute/docs/regions-zones'. |

5. Start installation
    ```
    source install.sh
    ```

Executing the script takes around 30 minutes. 
 
At the end of the installation process, MLflow URL for the web UI will be printed to the console. 
You can use it to browse the MLflow Tracking UI:

> Please, note:
> 1. At the end of process, MLflow URL will be printed to the console after the
   'MLflow UI can be accessed at the below URI:' message.
> 2. MLFLOW_TRACKING_EXTERNAL_URI variable will be set to MLflow URL in Cloud Shell.
> 3. MLFLOW_TRACKING_EXTERNAL_URI will be available in Notebook Terminal as well.
> 4. Cloud AI Platform services are not available every regions. Please check [Training regions](https://cloud.google.com/ai-platform/training/docs/regions)
>    and [compute regions](https://cloud.google.com/compute/docs/regions-zones/) (for Notebooks)

![MLflow logs](../../images/mlflow-ui-01.png)


## Creating AI Platform Notebooks Instance

The AI Platform Notebooks instance will be your interface of the development environment to define and save experimentation code.
Your notebooks and code files will be saved to Notebook local instance which is a stateless Docker container, therefore please use
[integrated Git to save your experiments](https://cloud.google.com/ai-platform/notebooks/docs/save-to-github).

Your Notebook instance will need to use a local MLflow server, which connects to the same Cloud SQL instance that is used by the previously provisioned
and dedicated MLflow instance (5th step).

We use the custom ML image created saved to Cloud Repository ($ML_IMAGE_URI) in the previous 6th step for the AI Notebooks instance. Image contains all required
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
    --metadata proxy-mode=service_account,container=$ML_IMAGE_URI,container-env-file=$GCS_BUCKET_NAME/notebook-env.txt
   ```

AI Notebooks instance will be created in 2-5 minutes. 
Required environment variables will be already set from the `container-env-file`.

The instance will show in the [AI Platform Notebooks instances](https://console.google.com/ai-platform/notebooks/instances).
You can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the **OPEN JUPYTERLAB** link.

> Building AI Notebook instances based on custom containers is a Beta feature that might change in the future.
> See [Using a custom container](https://cloud.google.com/ai-platform/notebooks/docs/custom-container)
> For more information.

## Verifying the Infrastructure

1. Open the JupyterLab in the AI Notebook instance

2. Clone the Github repository
    ```bash
    cd /home/jupyter
    git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp
    ```

3. Open `environment-test.ipynb Notebook` in `mlops-on-gcp/environments_setup/mlops-composer-mlflow` directory.

4. Run the cells of the Notebook. The Notebook has two parts:
    1. Running a local experiment that trains a simple Scikit-learn logistic regression model.
    2. Creating, deploying, and executing a simple Airflow workflow that trains a simple Scikit-learn logistic regression model.

5. Open `caip-training-test.ipynb Notebook` in `mlops-on-gcp/environments_setup/mlops-composer-mlflow` directory.

6. Run cells of the Notebook which has several parts. Please notice, you need to wait between couple of cells for the environmet readiness:
   1. Creating a training package with trainer routine and support files.
   2. Sending the training package in Cloud AI Platform Training. Checing the training job result from Cloud SQL database.
   3. Importing the training package and a simple workflow to Cloud Composer.
   4. Triggering Cloud Composer to run training package in Cloud AI Platform Training as a job. Checing the training job result from Cloud SQL database.

Both experiments are tracked by MLflow, where information is stored in Cloud SQL, and artifacts are stored in Cloud Storage.
You can open MLflow UI and check log information and artifacts produced by the experiments.  MLflow UI URL available in `MLFLOW_TRACKING_EXTERNAL_URI` environment variable.

![MLflow logs](../../images/mlflow-env-test.png)

Experiments names associated to these test runs:

* 'notebooks-test' - `environment-test.ipynb Notebook` metrics from local and Airflow traing runs. Results of both 5.1 and 5.2 sections above

* 'caipt-test' - `caip-training-test.ipynb Notebook` metrics from Cloud AI Platform Training job submited from notebook. Results of 6.2

* 'airflow-test' - `caip-training-test.ipynb Notebook` metrics from Airflow workflow managed training. Results of 6.4


## Uninstall and clean up the environment

Run the [destroy.sh](destroy.sh) script to turn down the services you provisioned:
```
./destroy.sh [PROJECT_ID] [DEPLOYMENT_NAME] [REGION] [ZONE]
```

This destroy script won't turn-down the AI Platform Notebook instance and won't clear IAM service account and key. You need to delete them manually.
