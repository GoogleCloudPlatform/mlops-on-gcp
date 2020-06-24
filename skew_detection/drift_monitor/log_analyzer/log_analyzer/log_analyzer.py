#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""An Apache beam pipeline that generates statistics and anomaly reports for a time
series of records in an AI Platform Prediction request-response log.
"""

import os
import logging
from enum import Enum
from typing import List, Optional, Text, Union, Dict, Iterable

import apache_beam as beam
import tensorflow_data_validation as tfdv

from apache_beam.options.pipeline_options import PipelineOptions
from datetime import datetime
from datetime import timedelta
from google.cloud import bigquery
from jinja2 import Template


from tensorflow_metadata.proto.v0 import statistics_pb2
from tensorflow_metadata.proto.v0 import schema_pb2
from tensorflow_metadata.proto.v0 import anomalies_pb2

from coders.beam_example_coders import InstanceCoder


_STATS_FILENAME = 'stats.pb'
_ANOMALIES_FILENAME = 'anomalies.pbtxt'
_SLICING_COLUMN_NAME = 'time_slice'
_SLICING_COLUMN_TYPE = schema_pb2.FeatureType.BYTES

_LOGGING_TABLE_SCHEMA = {
    'model': 'STRING',
    'model_version':  'STRING',
    'time': 'TIMESTAMP',
    'raw_data': 'STRING',
    'raw_prediction': 'STRING',
    'groundtruth': 'STRING'
}


def _validate_request_response_log_schema(request_response_log: str):
    """
    Validates that a provided request response log table
    conforms to schema.
    """

    query_template = """
       SELECT *
       FROM
           `{{ source_table }}`
       LIMIT 1
       """

    query = Template(query_template).render(
        source_table=request_response_log)

    client = bigquery.Client()
    query_job = client.query(query)
    rows = query_job.result()
    schema = {field.name: field.field_type for field in rows.schema}

    if schema != _LOGGING_TABLE_SCHEMA:
        raise TypeError("The table - {} - does not conform to the reuquest_response log table schema". format(
            request_response_log))


def _generate_query(table_name: str, model: str, version: str, start_time: str, end_time: str) -> str:
    """
    Generates a query that extracts a time series of records from an AI Platform Prediction
    request-response log.
    """

    sampling_query_template = """
        SELECT FORMAT_TIMESTAMP("%G-%m-%dT%T", time) as time, raw_data
        FROM 
            `{{ source_table }}`
        WHERE time BETWEEN '{{ start_time }}' AND '{{ end_time }}'
                AND model='{{ model }}' AND model_version='{{ version }}'
        """
    
    query = Template(sampling_query_template).render(
        source_table=table_name, 
        model=model, 
        version=version, 
        start_time=start_time, 
        end_time=end_time)

    return query


def _alert_if_anomalies(anomalies: anomalies_pb2.Anomalies, output_path: str):
    """
    Analyzes an anomaly protobuf and reports the status.

    Currently, the function just writes to a default Python logger.

    A more comprehensive alerting strategy will be considered in the future.
    """

    if list(anomalies.anomaly_info):
        logging.warn("Anomalies detected. The anomaly report uploaded to: {}".format(output_path))
    else:
        logging.info("No anomalies detected.")
    
    return anomalies


def analyze_log_records(
        request_response_log_table: str,
        model: str,
        version: str,
        start_time: datetime,
        end_time: datetime,
        output_path: str,
        schema: schema_pb2.Schema,
        baseline_stats: Optional[statistics_pb2.DatasetFeatureStatisticsList]=None,
        time_window: Optional[timedelta]=None,
        pipeline_options: Optional[PipelineOptions] = None,
): 
    """
    Computes statistics and detects anomalies for a time series of records 
    in an AI Platform Prediction request-response log.

    The function starts an Apache Beam job that calculates statistics and detects data anomalies
    in a time series of records retrieved from an AI Platform Prediction request-response log.
    Optionally, the function can also calculate stastics for a set of time slices within
    the time series. The output of the job is a statistics_pb2.DatasetFeatureStatisticsList
    protobuf with descriptive statistis and an anomalies_pb2.Anomalies protobuf
    with anomaly reports. The protobufs are stored to a GCS location. 

    Args:
      request_response_log_table: A full name of a BigQuery table
        with the request_response_log
      start_time: The start of the time series. The value will be rounded to minutes.
      end_time: The end of the time series. The value will be rounded to minutes. 
      output_path: The GCS location to output the statistics and anomaly
        proto buffers to. The file names will be `stats.pb` and `anomalies.pbtxt`. 
      schema: A Schema protobuf describing the expected schema.
      baseline_stats: If provided, the baseline statistics will be used to detect
        distribution anomalies.        
      time_window: If provided the  time series of records will be divided into 
        a set of consecutive time slices of the time_window width and the stats 
        will be calculated for each slice. 
      pipeline_options: Optional beam pipeline options. This allows users to
        specify various beam pipeline execution parameters like pipeline runner
        (DirectRunner or DataflowRunner), cloud dataflow service project id, etc.
        See https://cloud.google.com/dataflow/pipelines/specifying-exec-params for
        more details.
    """

    # Generate a BigQuery query
    end_time = end_time.replace(second=0, microsecond=0)
    start_time = start_time.replace(second=0, microsecond=0)
    query = _generate_query(
        table_name=request_response_log_table, 
        model=model, 
        version=version, 
        start_time=start_time.strftime('%Y-%m-%dT%H:%M:%S'), 
        end_time=end_time.strftime('%Y-%m-%dT%H:%M:%S'))

    # Configure slicing for statistics calculations
    stats_options = tfdv.StatsOptions(schema=schema)
    slicing_column = None
    if time_window:
        time_window = timedelta(
            days=time_window.days,
            seconds=(time_window.seconds // 60) * 60)

        if end_time - start_time > time_window:
            slice_fn = tfdv.get_feature_value_slicer(features={_SLICING_COLUMN_NAME: None})
            stats_options.slice_functions=[slice_fn]
            slicing_column = _SLICING_COLUMN_NAME 
            slicing_feature = schema.feature.add()
            slicing_feature.name = _SLICING_COLUMN_NAME
            slicing_feature.type = _SLICING_COLUMN_TYPE

    # Configure output paths 
    stats_output_path = os.path.join(output_path, _STATS_FILENAME)
    anomalies_output_path = os.path.join(output_path, _ANOMALIES_FILENAME)

    # Define an start the pipeline
    with beam.Pipeline(options=pipeline_options) as p:
        raw_examples = (p
           | 'GetData' >> beam.io.Read(beam.io.BigQuerySource(query=query, use_standard_sql=True)))

        examples = (raw_examples
           | 'InstancesToBeamExamples' >> beam.ParDo(InstanceCoder(schema, end_time, time_window, slicing_column)))

        stats = (examples
           | 'BeamExamplesToArrow' >> tfdv.utils.batch_util.BatchExamplesToArrowRecordBatches()
           | 'GenerateStatistics' >> tfdv.GenerateStatistics(options=stats_options))

        _ = (stats
            | 'WriteStatsOutput' >> beam.io.WriteToTFRecord(
                file_path_prefix=stats_output_path,
                shard_name_template='',
                coder=beam.coders.ProtoCoder(
                    statistics_pb2.DatasetFeatureStatisticsList)))

        anomalies = (stats
            | 'ValidateStatistics' >> beam.Map(tfdv.validate_statistics, schema=schema, previous_statistics=baseline_stats))

        _ = (anomalies
            | 'AlertIfAnomalies' >> beam.Map(_alert_if_anomalies, anomalies_output_path)
            | 'WriteAnomaliesOutput' >> beam.io.textio.WriteToText(
                file_path_prefix=anomalies_output_path,
                shard_name_template='',
                append_trailing_newlines=False))

