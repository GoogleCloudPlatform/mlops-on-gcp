# Analyzing and validating data in production ML

This series of hands on labs demonstrates techniques and best practices for analyzing and validating data in production ML settings. The labs cover the following topics:
- Developing data schemas
- Validating data in continuous training pipelines
- Validating data during model serving


## Preparing the lab environment
You will use the lab environment configured as on the below diagram:

![Lab env](/images/lab-env.png)

The core services in the environment are:
- ML experimentation and development - AI Platform Notebooks 
- Scalable, serverless model training - AI Platform Training  
- Scalable, serverless model serving - AI Platform Prediction 
- Machine learning pipelines - AI Platform Pipelines
- Distributed data processing - Cloud Dataflow  
- Analytics data warehouse - BigQuery 
- Artifact store - Google Cloud Storage 
- CI/CD tooling - Cloud Build
    
In this environment, all services are provisioned in the same [Google Cloud Project](https://cloud.google.com/storage/docs/projects). 

### Enabling Cloud Services

To enable Cloud Services utilized in the lab environment:
1. Launch [Cloud Shell](https://cloud.google.com/shell/docs/launching-cloud-shell)
2. Set your project ID
```
PROJECT_ID=[YOUR PROJECT ID]

gcloud config set project $PROJECT_ID
```
3. Use `gcloud` to enable the services
```
gcloud services enable \
cloudbuild.googleapis.com \
container.googleapis.com \
cloudresourcemanager.googleapis.com \
iam.googleapis.com \
containerregistry.googleapis.com \
containeranalysis.googleapis.com \
ml.googleapis.com \
dataflow.googleapis.com 
```



### Creating an instance of AI Platform Pipelines
The core component of the lab environment is **AI Platform Pipelines**. To create an instance of **AI Platform Pipelines** follow the [Setting up AI Platform Pipelines](https://cloud.google.com/ai-platform/pipelines/docs/setting-up) how-to guide. Make sure to enable the access to *https://www.googleapis.com/auth/cloud-platform* when creating a GKE cluster.


### Creating an instance of AI Platform Notebooks

An instance of **AI Platform Notebooks** is used as a primary experimentation/development workbench. Different labs may use different configurations. Refer to the lab README files for the detailed instructions on setting up the lab instance.

To provision the instance follow the [Create an new notebook instance](https://cloud.google.com/ai-platform/notebooks/docs/create-new) setup guide. Use the *TensorFlow Enterprise 2.1* no-GPU image. Leave all other settings at their default values.

After the instance is created, you can connect to [JupyterLab](https://jupyter.org/) IDE by clicking the *OPEN JUPYTERLAB* link in the [AI Platform Notebooks Console](https://console.cloud.google.com/ai-platform/notebooks/instances).

In the **JupyterLab**, open a terminal and clone this repository in the `home` folder.
```
cd
git clone https://github.com/GoogleCloudPlatform/mlops-on-gcp.git
```

From the `mlops-labs/workshops/tfx-caip-tf21` folder execute the `install.sh` script to install **TFX** and **KFP** SDKs.

```
cd mlops-on-gcp/workshops/tfx-caip-tf21
./install.sh
```

## Summary of lab exercises

### Lab-01-x - Exploratory data analysis and schema development using TensorFlow Data Validation.
In this lab, you will use the TensorFlow Data Validation (TFDV) library to analyze data and develop a data schema. There are multiple versions of this lab using different datasets. 



