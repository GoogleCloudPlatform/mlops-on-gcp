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

"""A command line interface to start a Beam pipeline to analyze a time series of records.
"""

import argparse
import datetime
import logging
import os
import re
import apache_beam as beam

from typing import List, Optional, Text, Union, Dict, Iterable
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from apache_beam.options.pipeline_options import GoogleCloudOptions

from tensorflow_data_validation import StatsOptions
from tensorflow_data_validation import load_statistics
from tensorflow_data_validation import load_schema_text

from analyzer.data_analyzer import analyze_records


_SETUP_FILE = './setup.py'

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--source_path',
        dest='source_path',
        type=str,
        required=True,
        help='Source path to CSV file')
    parser.add_argument(
        '--output_path',
        dest='output_path',
        type=str,
        required=True,
        help='An output path for statistics and anomaly protocol buffers')
    parser.add_argument(
        '--baseline_stats_file',
        dest='baseline_stats_file',
        type=str,
        help='A path to a baseline statistics file',
        required=False)

    known_args, pipeline_args = parser.parse_known_args()

    baseline_stats = None
    if known_args.baseline_stats_file:
        baseline_stats = load_statistics(known_args.baseline_stats_file)

    schema = load_schema_text(known_args.schema_file)

    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).setup_file = _SETUP_FILE

    logging.log(logging.INFO, "Starting the data analysis pipeline...")
    analyze_records(
        source_path=known_args.source_path,
        output_path=known_args.output_path,
        baseline_stats=baseline_stats,
        pipeline_options=pipeline_options)

