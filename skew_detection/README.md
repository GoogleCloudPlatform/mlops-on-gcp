# ML Model Monitoring: Serving Data Skew detection with AI Platform

This directory includes code example of how you can implement a serving data skew detection system for deployed ML
models to [Cloud AI Platform Prediction](https://cloud.google.com/ai-platform/prediction/docs).

## Dataset

The tutorials in this directory uses the [covertype](https://archive.ics.uci.edu/ml/datasets/covertype) from 
UCI Machine Learning Repository. The task is to Predict forest cover type from cartographic variables only.

We use this dataset to build a Keras classification model and deploy it to AI Platform prediction.

The dataset is preprocessed, split, and uploaded to the `gs://workshop-datasets/covertype` public GCS location. 

## Notebooks

[01_covertype_training_serving.ipynb](01_covertype_training_serving.ipynb) - This notebook shows how to use
request-response logging to BigQuery in AI Platform Prediction. The notebook covers:
 * Training and exporting a Keras model using TensorFlow 2.x
 * Deploying the exported SavedModel to AI Platform Prediction
 * Enabling request-response logging to BigQuery
    
[02_covertype_logs_parsing.ipynb](02_covertype_logs_parsing.ipynb) - This notebook shows how to parse and
analyze raw request-response logs in BigQuery. The notebook covers:
  * Creating a view using your dataset metadata to parse the raw request instances and response prediction 
    logged in BigQuery
  * Querying the view to retrieved structured logs.

[03_covertype_drift_detection_tfdv.ipynb](03_covertype_drift_detection_tfdv.ipynb) - This notebook shows how to
Use TensorFlow Data Validation (TFDV) to detect skews in request-response serving data. The notebook covers:
  * Creating a *reference schema* from the training data
  * Reading logs data from BigQuery
  * Using TFDV to generate *statistics* from the serving logs data 
  * Using TFDV to validate the statistics against the *reference schema*
  * Visualizing and display the statistics and anomalies
  * Analyzing how statistics change over time
  
[04_covertype_drift_detection_novelty_modeling.ipynb](04_covertype_drift_detection_novelty_modeling) - This notebook 
shows how to use the Elliptic Envlope novelty detection model to detect skews between data split (e.g. training and serving). 
Novelty detection models can identify whether an instance belongs to a population, or is considered as an outlier.
  * Generate mutated data with random feature value combinations 
  * Train Elliptic Envelope using the training data
  * Validate the normal and mutated data against the model
  * Implement Apache Beam pipeline that analyses request-response data from BigQuery
  * Display drift detection output

## Drift Monitor

[drift_monitor](drift_monitor) describes the architecture and implementation of an automated system for detecting 
training-serving data skew in machine learning (ML). The system introduces:

1. A [Dataflow Template](drift_monitor/log_analyzer) that utilizes TensorFlow Data Validation (TFDV) to identify skews 
and anomalies in the serving request-response data logged in BigQuery. 

2. A [scheduling mechanism](drift_monitor/job_scheduler) for executing the skew detection Dataflow Template using 
Cloud Tasks, with an easy-to-use Command Line Interface (CLI)

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
 
 



