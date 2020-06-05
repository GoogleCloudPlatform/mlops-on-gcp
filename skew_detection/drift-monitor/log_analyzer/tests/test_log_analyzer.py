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

import base64
import logging
import datetime
import json
import mock
import pytest

import tensorflow as tf

from tensorflow_data_validation import load_schema_text
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions
from log_analyzer import analyze_log_records, _validate_request_response_log_schema


def test_analyze_log_records():

    request_response_log_table = 'data_validation.covertype_classifier_logs_tf'
    project_id = 'mlops-dev-env'
    model = 'covertype_tf'
    version = 'v3'

    baseline_stats = None
    output_path = 'gs://mlops-dev-workspace/drift-monitor/output/covertype_tf/test'
    start_time = datetime.datetime.fromisoformat('2020-05-25T16:01:10')
    end_time = datetime.datetime.fromisoformat('2020-05-25T22:50:30')

    time_window = None
    time_window = datetime.timedelta(hours=1)

    schema_path = 'gs://mlops-dev-workspace/drift-monitor/schema/schema.pbtxt'
    schema = load_schema_text(schema_path)

    pipeline_options = PipelineOptions() 
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = project_id

    logging.getLogger().setLevel(logging.INFO)

    analyze_log_records(
        request_response_log_table=request_response_log_table,
        model=model,
        version=version,
        start_time=start_time,
        end_time=end_time,
        time_window=time_window,
        output_path=output_path,
        schema=schema, 
        baseline_stats=baseline_stats,
        pipeline_options=pipeline_options)


def test_validate_request_response_log_schema():

    request_response_log_table = 'data_validation.covertype_logs_tf'
    _validate_request_response_log_schema(request_response_log_table)
