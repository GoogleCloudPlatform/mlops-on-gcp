# AI Platform Prediction request-response Log Analyzer

This folder contains a sample [Dataflow Flex Template](https://cloud.google.com/dataflow/docs/guides/templates/overview) - **Log Analyzer** - designed to analyze data from [the AI Platform Prediction request-response log](https://cloud.google.com/ai-platform/prediction/docs/online-predict).


## Understanding Log Analyzer Design

The Log Analyzer template encapsulates an Apache Beam pipeline that analyzes data from the AI Platform Prediction request-response log. The template utilizes [TensorFlow Data Validation](https://www.tensorflow.org/tfx/guide/tfdv) to calculate descriptive statistics and detect data anomalies in a time series of records extracted from the log. 

### Log Analyzer workflow

The pipeline implements the following workflow:

![Workflow](/images/template-workflow.png)

1. Extract a time series of records from the request-response log table in BigQuery.
2. Convert the records to the `tensorflow_data_validation.type.BeamExample` format required by the Tensorflow Data Validation statistics generation API.
3. Use the [`tensorflow_data_validation.GenerateStatistics`](https://www.tensorflow.org/tfx/data_validation/api_docs/python/tfdv/GenerateStatistics) *PTransform* to calculate descriptive statistics for the time series of records. 
4. Detect data anomalies in the time series. Refer to the *Detecting data anomalies* section  for more information.
5. Log a warning in the Dataflow job log if any anomalies are detected.
6. Store the calculated statistics and anomalies protocol buffers to Google Cloud Storage location.

### Log Analyzer interface

The Log Analyzer Dataflow Template accepts the following runtime arguments


Name | Type | Optional |  Description
-----|------|----------|------------
request_response_log_table | String | No | A full name of the request-response log table in BigQuery
model | String | No | A name of the AI Platform Prediction model
version | String | No | A version of the AI Platform Prediction model
start_time | String | No | The beginning of a time series of records in the log in the ISO date-time format - YYYY-MM-DDTHH:MM:SS
end_time | String | No | The end of a time series of records in the log in the ISO date-time format - YYYY-MM-DDTHH:MM:SS
output_put | String | No | A GCS location for the ouput stats and anomalies.
schema_file | String | No | A GCS path to the schema file describing the the model's input interface
baseline_stats_file | String | Yes | A GCS path to a baseline statistics file
time_window | String | Yes | A time window for slice calculations. You must use the `m` or `h` suffixt to designate minutes or hours. For example, `60m` defines a 60 minute time window.



### Calculating descriptive statistics

The template will use `tensorflow_data_validation.GenerateStatistics` *PTransform* to calculate statistics for a full time series of records from `start_time` to `end_time` where `start_time` and `end_time` are the values for the `time` field in the AI Platform Prediction request-response log table.


## Deploying the Log Analyzer Dataflow Flext template

Use the `deploy_log_analyzer.sh` script to build and deploy the template.

## Triggering the Log Analyzer runs

After the template has been deployed you can trigger the Log Analyzer's runs using the `gcloud beta dataflow flex-template run` command or the helper utility - `dms` - from the `job_scheduler` folder. In addition to triggering immediate runs, the utility allows you to schedule future runs. Refer to the README file in the `job_scheduler` folder for more information.
