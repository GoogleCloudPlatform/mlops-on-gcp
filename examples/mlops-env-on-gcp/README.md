# Setting up an MLOps environment on GCP

This folder contains instructions that guide you through the process of setting up a GCP based MLOps environment as depicted on the below diagram.

![Reference topology](/images/mlops-env.png)

The core services in the environment are:
- [AI Platform Notebooks](https://cloud.google.com/ai-platform/notebooks/docs/): ML experimentation and development
- [AI Platform Training](https://cloud.google.com/ai-platform/training/docs/): Scalable, serverless model training 
- [AI Platform Prediction](https://cloud.google.com/ai-platform/prediction/docs/): Scalable, serverless model serving 
- [Dataflow](https://cloud.google.com/dataflow/docs): Distributed batch and streaming data processing
- [BigQuery](https://cloud.google.com/bigquery/docs): Scalable analytics data warehouse 
- [Google Cloud Storage](https://cloud.google.com/bigquery/docs): Artifact storage 
- [Kubeflow Pipelines](https://www.kubeflow.org/docs/pipelines/installation/standalone-deployment/): Kubeflow standalone machine learning pipeline deployed on [Google Kubernetes Engine (GKE)](https://cloud.google.com/kubernetes-engine/docs/)
- [Cloud SQL](https://cloud.google.com/sql/docs/mysql/connect-kubernetes-engine): Machine learning metadata management 
- [Cloud Build](https://cloud.google.com/cloud-build/docs/): CI/CD tooling to build and deploy custom container image
- [Container Registry](https://cloud.google.com/container-registry/docs/): secure, private container image storage
    
In this environment, all services are provisioned in the same [Google Cloud Project](https://cloud.google.com/storage/docs/projects). 

An instance of **AI Platform Notebooks** is used as a primary experimentation/development workbench. The instance is configured using a custom container image built with **Cloud Build** and hosted on **Container Registry** that should be optimized for a given ML project. In this example, you will configure the instance optimized for developing **Kubeflow Pipelines (KFP)** and TensorFlow Extended (TFX) solutions. 

The environment uses a [standalone deployment of Kubeflow Pipelines on GKE](https://www.kubeflow.org/docs/pipelines/installation/standalone-deployment/), as depicted on the below diagram:

![KFP Deployment](/images/kfp.png)

The KFP services are deployed to a GKE cluster and configured to use a **Cloud SQL**  instance for ML Metadata and **Google Cloud Storage** for artifact storage. The KFP services access the Cloud SQL through [Cloud SQL Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy). External clients use [Inverting Proxy](https://github.com/google/inverting-proxy) to interact with the KFP services.

The provisioning of the environment has been split into two hands-on labs.

## [Creating an AI Platform Notebook instance](creating-notebook-instance/README.md)

In the first lab you create an instance of **AI Platform Notebooks**.

## [Provisioning a standalone deployment of Kubeflow Pipelines](provisioning-kfp/README.md)

 In the second lab you provision other services comprising the environment, including a standalone deployment of **Kubeflow Pipelines**.

# Before you begin

You need to have **Project Owner**  permissions in your GCP project to walk through the labs.
