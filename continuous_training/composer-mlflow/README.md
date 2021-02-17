# Automated model training and evaluation using
* #### Scikit-learn
* #### Google Cloud Composer
* #### Goolge Cloud AI Platform Training
* #### MLflow

This folder contains notebooks to train Chicago taxi fare prediction models.
In general, both versions are go through this workflow:

1. Split public taxi fare dataset to train and eval data sets
2. Define a simple feature engineering to improve training accuracy and extract new features
3. Train model on training split using Scikit-learn RandomForestRegressor 
4. Test model on eval set 

In order to use this examples you need to provision a Cloud Composer orchestrated and MLflow integrated
environment described in this [README.md](../../environments_setup/mlops-composer-mlflow/README.md)

The core services in the environment are:
- [AI Platform Notebooks](https://cloud.google.com/ai-platform/notebooks/docs/): ML experimentation and development
- [AI Platform Training](https://cloud.google.com/ai-platform/training/docs/): Scalable, serverless model training
- [BigQuery](https://cloud.google.com/bigquery/docs): Scalable analytics data warehouse
- [Google Cloud Storage](https://cloud.google.com/bigquery/docs): Artifact storage

## Experimental, self-contained version: chicago_taxi_fare_experiment.ipynb
* Experimentals to train taxi fare prediction model inside of the notebook while strore metrics to MLflow tracking.
* Intendend to help understanding the Chicago taxi data set with different data visualisations and alternative model training pipelines.

## Cloud Composer orchestrated version: multi_model_trainer.ipynb

#### This notebook composed only for producing files for
* Cloud AI Platform Training Job Python package 
* Cloud Composer/Airflow DAG which orchestrates the complex training pipeline

#### Cells implement these main steps
1. Train arbitrary amount of models on AI Platform Training jobs. Training process metrics are stored in Mlflow
2. Evaluate and compare new models on evaluation data split
3. Compare the best model to previously trained model and choose the best
4. Register the new model in Mlflow registry if it performs better than previous model version.

#### Training parameters and metrics
All training parameters are randomized and stored in MLflow.
- number_of_estomators (number of random forest trees) are limited between 'range_of_estimators_lower' and 'range_of_estimators_upper' static variables.
- training and eval set size is limited in 'tasks' dictionary 'limit' key.

Model scrores are also stored in MLflow. This implementation calculates
- train_cross_valid_score_rmse_mean
- eval_cross_valid_score_rmse_mean
by Scikit-Learn [cross-validation method](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html)