# AI Platform Prediction - NVIDIA Triton Inference Server Basic Setup

This repo walks through the process of setting up NVIDIA Triton Inference Server into AI Platform Custom Container Prediction service.  This will be a simple setup with direct model server mode.

### Configure environment

From the console, open an instance of Cloud Shell.

Enable services:
```
gcloud services enable \
notebooks.googleapis.com \
compute.googleapis.com \
containerregistry.googleapis.com \
ml.googleapis.com \
artifactregistry.googleapis.com
```

### Create an AI Platform Notebook instance

In Cloud Shell, execute the following commands:
```
export INSTANCE_NAME="caip-triton"
export VM_IMAGE_PROJECT="deeplearning-platform-release"
export VM_IMAGE_FAMILY="tf-1-15-cpu"
export MACHINE_TYPE="n1-standard-2"
export LOCATION="us-central1-b"

gcloud beta notebooks instances create $INSTANCE_NAME \
  --vm-image-project=$VM_IMAGE_PROJECT \
  --vm-image-family=$VM_IMAGE_FAMILY \
  --machine-type=$MACHINE_TYPE --location=$LOCATION
```
(Optional) Detailed setup instructions can be found [here](https://cloud.google.com/ai-platform/notebooks/docs/create-new).

Go to the Notebook [console](https://console.cloud.google.com/ai-platform/notebooks/instances?_ga=2.230420892.1299696707.1591948252-1008316514.1591948252).  When the Notebook server is ready, click the `OPEN JUPYTERLAB` link.

In the `Launcher` tab, click on `Terminal` in the `Other` group.

Log into Google Cloud: `gcloud auth login`

Finally, clone this repo into the Notebook instance.  For the rest of this lab, we will be using a guided notebook.





