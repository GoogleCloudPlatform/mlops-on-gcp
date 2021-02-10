# Automated model training and evaluation using
* #### Scikit-learn
* #### Google Cloud Composer
* #### Goolge Cloud AI Platform Training
* #### MLflow

This folder contains notebooks to train Chicago taxi fare prediction models in two approaches.
In general, both versions are go through this workflow:

1. Split public taxi fare dataset to train and eval data sets
2. Define a simple feature engineering to improve training accuracy and extract new features
3. Train model on training split using Scikit-learn RandomForestRegressor 
4. Test model on eval set 

## ChicagoTaxiFareTrainer.ipynb - The manual version
* Experimentals of routines to train taxi fare prediction model inside of the notebook.
* Intendend to help understanding the Chicago taxi data set by different data visualisations
* Helps evaluate the applied training pipeline.

## multi_model_trainer.ipynb - The automated version
Produces:
* Trainer package
* Cloud Composer/Airflow DAG



1. Train two models on AI Platform Training jobs. Training process metrics are stored in Mlflow
2. Evaluate new models on evaluation data split
3.  Validate and compare new model to previously trained models and select the best new one
4.  Register the blessed new model in Mlflow registry

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
