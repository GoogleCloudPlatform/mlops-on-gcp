# AI Platform Prediction request-response Log Analyzer

This folder contains a sample Dataflow Flex Template - **Log Analyzer** - designed to analyze data from [the AI Platform Prediction request-response log](https://cloud.google.com/ai-platform/prediction/docs/online-predict).

The template utilizes [TensorFlow Data Validation](https://www.tensorflow.org/tfx/guide/tfdv) to calculate descriptive statistics and detect data anomalies in a time series of records from the log. 

Use the `deploy_log_analyzer.sh` script to build and deploy the template.

After the template has been deployed you can trigger the Log Analyzer's runs using the `gcloud beta dataflow flex-template run` command or the helper utility - `dms` - from the `job_scheduler` folder. In addition to triggering immediate runs, the utility allows you to schedule future runs. Refer to the README file in the `job_scheduler` folder for more information.
