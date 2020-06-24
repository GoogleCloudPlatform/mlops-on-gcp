# Creating an AI Platform Notebooks instance

This lab walks you through provisiong of  an AI Platfom Notebooks instance using on a custom container image.

The accompanying lab - `provisioning-kfp` - describe the steps to provision other services in the MLOps environment, including a standalone deployment of Kubeflow Pipelines.

## Enabling the required cloud services

In addition to the [services enabled by default](https://cloud.google.com/service-usage/docs/enabled-service), the following additional services must be enabled to provision an instance of **AI Platform Notebooks**:

1. Compute Engine
1. Container Registry
1. Cloud Build

Use [GCP Console](https://console.cloud.google.com/) or `gcloud` command line interface in [Cloud Shell](https://cloud.google.com/shell/docs/) to [enable the required services](https://cloud.google.com/service-usage/docs/enable-disable) . 

To enable the required services using `gcloud`:
1. Start GCP [Cloud Shell](https://cloud.google.com/shell/docs/)
2. Make sure that **Cloud Shell** is configured to use your project
```
PROJECT_ID=[YOUR_PROJECT_ID]

gcloud config set project $PROJECT_ID
```

3. Enable services
```
gcloud services enable \
compute.googleapis.com \
container.googleapis.com \
cloudbuild.googleapis.com 

```

## Creating an **AI Platform Notebooks** instance

You will use a custom container image with KFP and TFX SDKs pre-installed to create your instance. 

### Building a custom docker image:

1. In **Cloud Shell**,  create a working folder in your `home` directory
```
cd
mkdir lab-workspace
cd lab-workspace
```

2. Create the requirements file with the Python packages to deploy to your instance
```
cat > requirements.txt << EOF
pandas<1.0.0
click==7.0
tfx==0.21.2
kfp==0.2.5
EOF
```


3. Create the Dockerfile defining you custom container image
```
cat > Dockerfile << EOF
FROM gcr.io/deeplearning-platform-release/base-cpu:m42
RUN apt-get update -y && apt-get -y install kubectl
RUN curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64 \
&& chmod +x skaffold \
&& mv skaffold /usr/local/bin
COPY requirements.txt .
RUN python -m pip install -U -r requirements.txt --ignore-installed PyYAML==5.3.1
EOF
```

4. Build the image and push it to your project's **Container Registry**

```
IMAGE_NAME=mlops-dev
TAG=latest
IMAGE_URI="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${TAG}"

gcloud builds submit --timeout 15m --tag ${IMAGE_URI} .
```

### Provisioning an AI Platform notebook instance

You can provision an instance of **AI Platform Notebooks** using  [GCP Console](https://cloud.google.com/ai-platform/notebooks/docs/custom-container) or using the `gcloud` command. To provision the instance using `gcloud`.

```
ZONE=[YOUR_ZONE]
INSTANCE_NAME=[YOUR_INSTANCE_NAME]

IMAGE_FAMILY="common-container"
IMAGE_PROJECT="deeplearning-platform-release"
INSTANCE_TYPE="n1-standard-4"
METADATA="proxy-mode=service_account,container=$IMAGE_URI"

gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --image-family=$IMAGE_FAMILY \
    --machine-type=$INSTANCE_TYPE \
    --image-project=$IMAGE_PROJECT \
    --maintenance-policy=TERMINATE \
    --boot-disk-device-name=${INSTANCE_NAME}-disk \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-ssd \
    --scopes=cloud-platform,userinfo-email \
    --metadata=$METADATA
```


### Accessing JupyterLab IDE

After the instance is created, you can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the *OPEN JUPYTERLAB* link.

