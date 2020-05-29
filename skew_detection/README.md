# ML Model Monitoring: Serving Data Skew detection with AI Platform

This directory includes code example of how you can implement a serving data skew detection system for deployed ML
models to [Cloud AI Platform Prediction](https://cloud.google.com/ai-platform/prediction/docs).

## Dataset

The tutorials in this directory uses the [covertype](https://archive.ics.uci.edu/ml/datasets/covertype) from 
UCI Machine Learning Repository. The task is to Predict forest cover type from cartographic variables only.

We use this dataset to build a Keras classification model and deploy it to AI Platform prediction.

The dataset is preprocessed, split, and uploaded to the `gs://workshop-datasets/covertype` public GCS location. 

## Notebooks

[01_covertype_training_serving.ipynb](01_covertype_training_serving.ipynb) - This notebook shows how to:
 * Train and export a Keras model using TensorFlow 2.x
 * Deploy the exported SavedModel to AI Platform Prediction
 * Enable request-response logging to BigQuery
    
[02_covertype_logs_parsing.ipynb](02_covertype_logs_parsing.ipynb) - This notebook shows how to:
  * Create a view using your dataset metadata to parse the raw request instances and response prediction 
    logged in BigQuery
  * Query the view to retrieved structured logs.

[03_covertype_drift_detection_tfdv.ipynb](03_covertype_drift_detection_tfdv.ipynb) - This notebook shows how to:
  * Create and fix a *reference schema* from the training data
  * Read and logs data from BigQuery
  * Use TFDV to generate *statistics* from the serving logs data 
  * Use TFDV to validate the statistics against the *reference schema*
  * Visualize and display the statistics and anomalies
  * Analyze how statistics change over time

## Drift Monitor

## Workload Simulator

In order to simulate prediction serving workload for the covertype classification model deployed to AI Platform, 
and generate request-response logs to BigQuery, you can use one of the following methods:
    
 1. You can use the [covertype_skewed_data_generation.ipynb](workload_simulator/covertype_skewed_data_generation.ipynb)
 notebook to generate both normal and skewed data points. The notebook then uses the generated data points to calls the 
 deployed model version to AI Platform for predictions. This generates request-response logs to BigQuery 
  
 2. Alternatively, you can load the [bq_prediction_logs.csv](workload_simulator/bq_prediction_logs.csv) 
 data file to your BigQuery request-response logs table. 
 The CSV file includes sample request-response logs with 2000 normal and 1000 skewed data points. 
 See [loading data to BigQuery from a local data source](https://cloud.google.com/bigquery/docs/loading-data-local)
 
 



