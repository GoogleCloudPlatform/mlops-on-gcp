# AI Platform Prediction request-response Log Analyzer

This folder contains a sample [Dataflow Flex Template](https://cloud.google.com/dataflow/docs/guides/templates/overview) - **Log Analyzer** - designed to analyze data from [the AI Platform Prediction request-response log](https://cloud.google.com/ai-platform/prediction/docs/online-predict).


## Log Analyzer Design

The Log Analyzer template encapsulates an Apache Beam pipeline that analyzes data from the AI Platform Prediction request-response log. The template utilizes [TensorFlow Data Validation](https://www.tensorflow.org/tfx/guide/tfdv) to calculate descriptive statistics and detect data anomalies in a time series of records extracted from the log. 

The pipeline implements the following workflow:

1. Extract a time series of records from the request-response log table in BigQuery.
2. Convert the records to the `tensorflow_data_validation.type.BeamExample` format required by the Tensorflow Data Validation statistics generation API.
3. Use the [`tensorflow_data_validation.GenerateStatistics`](https://www.tensorflow.org/tfx/data_validation/api_docs/python/tfdv/GenerateStatistics) *PTransform* to calculate descriptive statistics for the time series of records. If configured, the pipeline can also calculate statistics over a series of time slices with the time series.
4. Detect data anomalies in the time series. Refer to the *Supported data anomalies* section of the README for more information.
5. 


## Deploying the Log Analyzer Dataflow Flext template

Use the `deploy_log_analyzer.sh` script to build and deploy the template.

## Triggering the Log Analyzer runs

After the template has been deployed you can trigger the Log Analyzer's runs using the `gcloud beta dataflow flex-template run` command or the helper utility - `dms` - from the `job_scheduler` folder. In addition to triggering immediate runs, the utility allows you to schedule future runs. Refer to the README file in the `job_scheduler` folder for more information.
