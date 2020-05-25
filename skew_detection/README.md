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

[04_covertype_deploy_run_drift_detector_template.ipynb](04_covertype_deploy_run_drift_detector_template.ipynb) -
This notebook shows how to:
 * Deploy the [drift detector](drift_monitor/drift_detector) Dataflow pipeline as a Dataflow Flex Template to GCP.
 The drift detector use TensorFlow Data Validation (TFDV) to validate the serving data against 
 baseline schema and statistics
 * Run the drift_analyzer template to analyze the logged request-response serving data in BigQuery


## Drift Monitor

## Workload Simulator

We provide an [online prediction workload simulator](workload_simulator) to call model version deployed in AI Platform
Prediction and generate request-response logs to BigQuery. The workload simulator includes:
    
 1. [covertype_skewed_data_generation.ipynb](workload_simulator/covertype_skewed_data_generation.ipynb) - This notebook 
 generates two sets of data: 1) normal dataset containing sampled points from the validation split, and 2) skewed dataset
 by applying some modification to the feature values.
 
 2. [online_prediction_simulator.py](workload_simulator/online_prediction_simulator.py) - This script takes data files 
 (e.g. files in [serving_data](workload_simulator/serving_data)) and calls the model version deployed to
  AI Platform Prediction. The simulation is executed with respect to a specified duration.
  
 3. [bq_prediction_logs.csv](workload_simulator/bq_prediction_logs.csv) - This CSV file includes logs 
 generated from running the *online_prediction_simulator.py* for 3 days using, using normal dataset in the first two days
 and the skewed dataset in the third day. You can load them directly to your BigQuery request-response logs table. See
 [loading data to BigQuery from a local data source](https://cloud.google.com/bigquery/docs/loading-data-local)
 
 



