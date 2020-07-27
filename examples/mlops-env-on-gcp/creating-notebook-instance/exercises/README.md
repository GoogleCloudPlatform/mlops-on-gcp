# Creating an AI Platform Notebooks instance

**Learning Objectives:**
 1. Write a Dockerfile to define a custom image
 2. Build and push the image to your Container Registry
 2. Create an AI Platform Notebook using a custom container image
 
In this lab, you will provision an AI Platfom Notebooks instance using a custom container image.

The accompanying lab - `provisioning-kfp` - describe the steps to provision other services in the MLOps environment, including a standalone deployment of Kubeflow Pipelines.

## Enabling the required cloud services

In addition to the [services enabled by default](https://cloud.google.com/service-usage/docs/enabled-service), the following additional services must be enabled to provision an instance of **AI Platform Notebooks**:

1. Compute Engine
1. Container Registry
1. Cloud Build

Use [GCP Console](https://console.cloud.google.com/) or `gcloud` command line interface in [Cloud Shell](https://cloud.google.com/shell/docs/) to [enable the required services](https://cloud.google.com/service-usage/docs/enable-disable) . 

You can enable the required services using `gcloud`:
1. Start GCP [Cloud Shell](https://cloud.google.com/shell/docs/)
2. Make sure that **Cloud Shell** is configured to use your project. In Cloud Shell, bype the following commands. Replace `[YOUR_PROJECT_ID]` with your GCP Project ID.

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
tfx==0.21.4
kfp==0.5.1
EOF
```


3. TODO: Create a Dockerfile defining your custom container image within the `lab-workspace` directory. Your Dockerfile should execute the following steps:
 - use FROM to define the base image `gcr.io/deeplearning-platform-release/base-cpu:m42`. This will be used to start the build process. 
 - use RUN to execute the following directives
     - update `apt-get` and use apt-get to install `kubectl`
     - use `curl` to download `skaffold` using 
     ```bash 
        curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64
      ````
     - change permissions on `skaffold` with 
     ```bash
     chmod +x skaffold
     ```
     - move `skaffold` to the `/usr/local/bin` directory with 
     ```bash
     mv skaffold /usr/local/bin
     ```
 - use COPY to copy the `requirements.txt` file you wrote above 
 - use RUN to install the requirements using 
 ```bash 
 python -m pip install -U -r requirements.txt --ignore-installed PyYAML==5.3.1
 ```

4. TODO: Build the image and push it to your project's **Container Registry**. 

Use `gcloud builds submit` to submit a build using Google Cloud Build. Use the `--tag` flag for Cloud Build to build using the Dockerfile you created above. The tag should have the format `gcr.io/<YOUR_PROJECT_ID>/mlops-dev:latest`

### Provisioning an AI Platform notebook instance

5. TODO: Provision an instance of **AI Platform Notebooks** using the `gcloud compute instances create` command with the following specifications:
    - the `zone` should be your compute zone
    - the `image-family` should be "common-container"
    - the `machine-type` should be an n1 standard-4 machine. See all machine types [here](https://cloud.google.com/compute/docs/machine-types).
    - the `maintenance-policy` should be set to TERMINATE
    - the `boot-disk-device-name` should have the format `<YOUR_INSTANCE_NAME>-disk`
    - the `boot-disk-size` should be 100GB
    - the `boot-disk-type` should be set to a SSD persistent disk
    - the `scopes` should be `cloud-platform` and `userinfo-email`
    - the `metatdata` should have the follow key value pairs:
        - proxy-mode=service_account
        - container="gcr.io/<YOUR_PROJECT_ID>/mlops-dev:latest"

### Accessing JupyterLab IDE

After the instance is created, you can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the *OPEN JUPYTERLAB* link.

