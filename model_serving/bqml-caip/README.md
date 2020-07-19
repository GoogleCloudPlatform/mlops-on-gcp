# BQML Model Export to AI Platform Prediction

This set of notebooks illustrates the concepts of training a model in BQML, extracting the model, and then loading the model to AI Platform Prediction for online serving, as well as orchestrating the workflow in Kubeflow Pipelines.

In order to run these notebooks, the following setup will need to be performed.  Ensure a GCP project is already created.

### Configure environment

From the console, open an instance of Cloud Shell.

Set project:
```
export PROJECT_ID=[]
gcloud config set project ${PROJECT_ID}
```
Enable services:
```
gcloud services enable \
bigquery.googleapis.com \
ml.googleapis.com \
notebooks.googleapis.com
```
### Create an AI Platform Notebook instance

In Cloud Shell, execute the following commands:
```
export INSTANCE_NAME="bqml-caip"
export VM_IMAGE_PROJECT="deeplearning-platform-release"
export VM_IMAGE_FAMILY="tf-1-15-cpu"
export MACHINE_TYPE="n1-standard-4"
export LOCATION="us-central1-b"

gcloud beta notebooks instances create $INSTANCE_NAME \
  --vm-image-project=$VM_IMAGE_PROJECT \
  --vm-image-family=$VM_IMAGE_FAMILY \
  --machine-type=$MACHINE_TYPE --location=$LOCATION
```
(Optional) Detailed setup instructions can be found [here](https://cloud.google.com/ai-platform/notebooks/docs/create-new).

Go to the Notebook [console](https://console.cloud.google.com/ai-platform/notebooks/instances?_ga=2.230420892.1299696707.1591948252-1008316514.1591948252).  When the Notebook server is ready, click the `OPEN UPYTERLAB` link.

Once the Notebook is opened, click on `Terminal` and type the following command:
```
pip install kfp
```
Finally, clone this repo into the Notebook instance.

### Create an AI Platform Pipelines instance

Follow the instructions for [Setting up KF Pipelines](https://cloud.google.com/ai-platform/pipelines/docs/getting-started#set_up_your_instance) to create an instance of AI Platform Kubeflow Pipelines.

After the KF Pipelines instance is created, from the console, click on `SETTINGS` and locate the `"host=..."` under "Connect to this Kubeflow Pipelines instance..."  Use this value for KFPHOST in the [Pipelines](02-bqml-to-caip-pipeline.ipynb) notebook.



