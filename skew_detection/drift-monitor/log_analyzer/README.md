# AI Platform Prediction request-response log analyzer

This folder contains a sample Dataflow Flex Template designed to analyze data from the AI Platform Prediction request-response log.

The template utilizes TensorFlow Data Validation to calculate descriptive statistics and detect data anomalies in a time series of records from the log. 

Use the `deploy_log_analyzer.sh` script to build and deploy the template.

After the template has been deployed you can trigger the log analyzer's runs using the `gcloud beta dataflow flex-template run` command or the helper utility - `dms` - from the `job_scheduler` folder. In addition to trigger immediate runs, the utility allows you to schedule future runs. Refer to the README file in the `job_scheduler` folder for more information.
