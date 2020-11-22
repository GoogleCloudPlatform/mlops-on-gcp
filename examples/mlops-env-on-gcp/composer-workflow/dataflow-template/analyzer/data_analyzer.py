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
"""An Apache beam pipeline that generates statistics and anomaly reports for taxi fare records.
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

from tensorflow_metadata.proto.v0 import statistics_pb2
from tensorflow_metadata.proto.v0 import schema_pb2
from tensorflow_metadata.proto.v0 import anomalies_pb2


_STATS_FILENAME = 'stats.pb'
_ANOMALIES_FILENAME = 'anomalies.pbtxt'

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


def analyze_records(
        source_path: str,
        output_path: str,
        baseline_stats: Optional[statistics_pb2.DatasetFeatureStatisticsList]=None,
        pipeline_options: Optional[PipelineOptions] = None,
): 
    """
    Computes statistics and detects anomalies for a time series of records..

    The function starts an Apache Beam job that calculates statistics and detects data anomalies
    in a time series of records. The output of the job is a statistics_pb2.DatasetFeatureStatisticsList
    protobuf with descriptive statistis and an anomalies_pb2.Anomalies protobuf
    with anomaly reports. The protobufs are stored to a GCS location. 

    Args:
      source_path: A full name of a BigQuery table
        with the request_response_log
      output_path: The GCS location to output the statistics and anomaly
        proto buffers to. The file names will be `stats.pb` and `anomalies.pbtxt`. 
      baseline_stats: If provided, the baseline statistics will be used to detect
        distribution anomalies.        
      pipeline_options: Optional beam pipeline options. This allows users to
        specify various beam pipeline execution parameters like pipeline runner
        (DirectRunner or DataflowRunner), cloud dataflow service project id, etc.
        See https://cloud.google.com/dataflow/pipelines/specifying-exec-params for
        more details.
    """
    # Configure slicing for statistics calculations
    stats_options = tfdv.StatsOptions()
    slicing_column = None

    # Configure output paths 
    stats_output_path = os.path.join(output_path, _STATS_FILENAME)
    anomalies_output_path = os.path.join(output_path, _ANOMALIES_FILENAME)

    # Define an start the pipeline
    with beam.Pipeline(options=pipeline_options) as p:
        stats = (p
           | 'GenerateStatistics' >> tfdv.generate_statistics_from_csv(source_path))
        
        schema = (stats
           |  tfdv.infer_schema(statistics=stats))
        
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

