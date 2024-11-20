# Exporting a BigQuery ML model to AI Platform Prediction

This set of notebooks illustrates the following concepts:
* Training a model in BigQuery ML. 
* Extracting the model. 
* Loading the model into AI Platform Prediction for online serving. 
* Orchestrating the workflow in Kubeflow Pipelines.

In order to run these notebooks, you must have a Google Cloud project and perform the following steps for setup. 

### Configure your environment

1. From the Cloud console, open an instance of Cloud Shell.

1. Specify the Google Cloud project:
   ```
   export PROJECT_ID=[]
   gcloud config set project ${PROJECT_ID}
   ```
1. Enable services:
   ```
   gcloud services enable \
   bigquery.googleapis.com \
   ml.googleapis.com \
   notebooks.googleapis.com
   ```
### Create an AI Platform Notebook instance

1. In Cloud Shell, execute the following commands:
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
1. (Optional) Review additional AI Platform notebook setup instructions on the [Create a new notebook instance](https://cloud.google.com/ai-platform/notebooks/docs/create-new) documentation.
1. Go to the Notebook [console](https://console.cloud.google.com/ai-platform/notebooks/instances?_ga=2.230420892.1299696707.1591948252-1008316514.1591948252).
1. When the Notebook server is ready, click the `OPEN JUPYTERLAB` link.
1. Once the Notebook is opened, click on `Terminal` and type the following command:
   ```
   pip install kfp
   ```
1. Clone this repo into the Notebook instance.

### Create an AI Platform Pipelines instance

1. To create an instance of AI Platform Kubeflow Pipelines, follow the instructions for [Setting up Kubeflow Pipelines](https://cloud.google.com/ai-platform/pipelines/docs/getting-started#set_up_your_instance) .
1. After the Kubeflow Pipelines instance is created, from the Cloud Console, click `SETTINGS` and locate the `"host=..."` under "Connect to this Kubeflow Pipelines instance..."  Use this value for KFPHOST in the [Pipelines notebook](02-bqml-to-caip-pipeline.ipynb).
