# AI Platform Prediction request-response Log Analyzer

This folder contains a sample [Dataflow Flex Template](https://cloud.google.com/dataflow/docs/guides/templates/overview) - **Log Analyzer** - designed to analyze data from [the AI Platform Prediction request-response log](https://cloud.google.com/ai-platform/prediction/docs/online-predict).


## Understanding Log Analyzer Design

The Log Analyzer template encapsulates an Apache Beam pipeline that analyzes data from the AI Platform Prediction request-response log. The template utilizes [TensorFlow Data Validation](https://www.tensorflow.org/tfx/guide/tfdv) to calculate descriptive statistics and detect data anomalies in a time series of records extracted from the log. 

### Log Analyzer workflow

The pipeline implements the following workflow:

![Workflow](/images/template-workflow.png)

1. Extract a time series of records from the request-response log table in BigQuery.
2. Convert the records to the `tensorflow_data_validation.type.BeamExample` format required by the Tensorflow Data Validation statistics generation API.
3. Calculate descriptive statistics for the time series of records. Refer to *Calculating description statistics* section for more information.
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
schema_file | String | No | A GCS path to the reference schema file describing the the model's input interface
baseline_stats_file | String | Yes | A GCS path to a baseline statistics file
time_window | String | Yes | A time window for slice calculations. You must use the `m` or `h` suffixt to designate minutes or hours. For example, `60m` defines a 60 minute time window.

Currently, the log analyzer supports two types of AI Platform Prediction inputs, as captured in the request-response log's `raw_data` field:

1. Simple JSON instances:
```
{ 
    "instances": [
        <simple JSON object>,
        ...
     ]
}           
```

For example:
```
{
    "instances": [
        {
            "Elevation": 120.0,
            "Wilderness_Area": "Commanche",
            ...
        },
        {
            "Elevation": 300.5,
            "Wilderness_Area": "Rawah",
            ...
         },
     ]
}
```

2. Simple list instances:

```
{ 
    "instances": [
        <simple list>,
        ...
     ]
}   
```

For example

```
{
    "instances": [
        [100, 0.2, "Rawah"],
        [200, 0.3, "Commanche"]
}
```


### Calculating descriptive statistics

The template uses [`tensorflow_data_validation.GenerateStatistics`](https://www.tensorflow.org/tfx/data_validation/api_docs/python/tfdv/GenerateStatistics) *PTransform* to calculate statistics for a full time series of records from `start_time` to `end_time` where `start_time` and `end_time` are the values for the `time` field in the AI Platform Prediction request-response log table. For more information on what type of statistics are calculated refer to the [TensorFlow Data Validation](https://www.tensorflow.org/tfx/guide/tfdv) documentation.

If the optional `time_window` parameter is provided, the time series of records is divided into a set of time slices of the `time_window` width and statistics are calculated for each time slice.

![time slicing](/images/time_slicing.png)

### Detecting data anomalies

The pipeline uses the `tensorflow_data_validation.validate_statistics` function to detect data anomalies. Refer to the [TensorFlow Data Validation](https://www.tensorflow.org/tfx/guide/tfdv) documentation for more information about the types of anomalies detected by the pipeline.

If the opional `baseline_stats_file` template argument is provided it will be passed as the `previous_statistics` argument to `validate_statistics`.

If the reference schema, passed as the `schema_file` template argument, includes skew comparator threshold directives the distribution skew metrics will be calculated for the annotated categorical variables.

If any anomalies are detected, the pipeline logs a warning message in the corresponding Dataflow job's execution log. In future, additional alerting mechanisms may be added.


## Deploying the Log Analyzer Dataflow Flext template

Use the `deploy_log_analyzer.sh` script to build and deploy the template.

## Triggering the Log Analyzer runs

After the template has been deployed you can trigger the Log Analyzer's runs using the `gcloud beta dataflow flex-template run` command or the helper utility - `dms` - from the `job_scheduler` folder. In addition to triggering immediate runs, the utility allows you to schedule future runs. Refer to the README file in the `job_scheduler` folder for more information.
