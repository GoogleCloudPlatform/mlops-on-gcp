# ML Model Monitoring: Serving Data Skew detection with AI Platform

This directory includes code example of how you can implement a serving data skew detection system for deployed ML
models to AI Platform Prediction.

## Notebooks

1. [01_covertype_training_serving.ipynb](01_covertype_training_serving.ipynb) - This notebook shows how to:
    * Train and export a Keras model using TensorFlow 2.x
    * Deploy the exported SavedModel to AI Platform Prediction
    * Enable request-response logging to BigQuery
    * Parse the raw logs in BigQuery
    
2. [02_covertype_skewed_data_generation.ipynb](02_covertype_skewed_data_generation.ipynb) - This notebooks 
provides sample code to generate skewed data as serving workload to the deployed model to AI Platform Prediction.
The logged serving data to BigQuery can then be analyzed and visualized.

3. [03_covertype_deploy_run_skew_analyzer_template.ipynb](03_covertype_deploy_run_drift_analyzer_template.ipynb) -
This notebook shows how to:
    * Deploy the [skew detector](skew_detector) Dataflow pipeline as a Dataflow Flex Template to GCP.
     The drift detector use TensorFlow Data Validation (TFDV) to validate the serving data against 
     baseline schema and statistics.
    * Run the Drift Analyzer template to analyze the logged request-response serving data in BigQuery

4. [04_covertype_analyze_skews_with tfdv.ipynb](04_covertype_analyze_skews_with tfdv.ipynb) - This notebook
shows how to:
    * Visualize the computed statistics of the serving data, and compare it against a baseline statistics from 
    the training data.
    * List the anomalies - if any - detected by the skew detector.
