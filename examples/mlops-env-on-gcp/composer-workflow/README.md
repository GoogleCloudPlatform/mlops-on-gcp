# Automated model training and evaluation on Cloud Composer

This folder contains instructions that guide you through this workflow:

1. Split public taxi fare estimation dataset to CSV files using Airflow BigQuery operators
2. Train two models on AI Platform Training jobs. Training process metrics are stored in Mlflow
3. Evaluate new models on evaluation data split
4. Validate and compare new model to previously trained models and select the best new one
5. Register the blessed new model in Mlflow registry

![Workflow topology](/images/!!! TODO !!!)

The core services in the environment are:

- [AI Platform Notebooks](https://cloud.google.com/ai-platform/notebooks/docs/): ML experimentation and development
- [AI Platform Training](https://cloud.google.com/ai-platform/training/docs/): Scalable, serverless model training
- [AI Platform Prediction](https://cloud.google.com/ai-platform/prediction/docs/): Scalable, serverless model serving
- [BigQuery](https://cloud.google.com/bigquery/docs): Scalable analytics data warehouse
- [Google Cloud Storage](https://cloud.google.com/bigquery/docs): Artifact storage
- [Cloud SQL](https://cloud.google.com/sql/docs/mysql/connect-kubernetes-engine): Machine learning metadata management
- [Cloud Build](https://cloud.google.com/cloud-build/docs/): CI/CD tooling to build and deploy custom container image


TensorFlow Data Validation example:
https://nbviewer.jupyter.org/github/tensorflow/tfx/blob/master/docs/tutorials/data_validation/tfdv_basic.ipynb
