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
import re

from typing import List, Optional, Text, Union, Dict, Iterable
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from apache_beam.options.pipeline_options import GoogleCloudOptions

from tensorflow_data_validation import StatsOptions
from tensorflow_data_validation import load_statistics
from tensorflow_data_validation import load_schema_text

from analyzer.data_analyzer import generate_statistics


_SETUP_FILE = './setup.py'

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '--bq_project_id',
        dest='bq_project_id',
        type=str,
        required=True,
        help='Source BigQuery project')
    parser.add_argument(
        '--query',
        dest='query',
        type=str,
        required=True,
        help='BigQuery select query')
    parser.add_argument(
        '--start_time',
        dest='start_time',
        type=str,
        required=True,
        help='The beginning of a time series of log records in the ISO datetime format: YYYY-MM-DDTHH:MM:SS')
    parser.add_argument(
        '--end_time',
        dest='end_time',
        type=str,
        required=True,
        help='The end of a time series of log records in the ISO datetime format: YYYY-MM-DDTHH:MM:SS')
    parser.add_argument(
        '--output_path',
        dest='output_path',
        type=str,
        required=True,
        help='An output path for statistics and anomaly protocol buffers')
    parser.add_argument(
        '--schema_file',
        dest='schema_file',
        type=str,
        help='A path to a schema file',
        required=True)
    parser.add_argument(
        '--baseline_stats_file',
        dest='baseline_stats_file',
        type=str,
        help='A path to a baseline statistics file',
        required=False)
    parser.add_argument(
        '--time_window',
        dest='time_window',
        type=str,
        help='A time window to use for time slice calculations. You must use the m or h suffix to designate minutes or hours',
        required=False)

    known_args, pipeline_args = parser.parse_known_args()

    start_time = datetime.datetime.strptime(known_args.start_time, '%Y-%m-%dT%H:%M:%S')
    end_time = datetime.datetime.strptime(known_args.end_time, '%Y-%m-%dT%H:%M:%S') 

    if not start_time: 
        raise ValueError("Wrong format of start_time: {}".format(known_args.start_time))

    if not end_time: 
        raise ValueError("Wrong format of endtime_time: {}".format(known_args.end_time))

    if start_time >= end_time:
        raise ValueError("The end_time cannot be earlier than the start_time")

    time_window=None
    if known_args.time_window:
        if not re.fullmatch('[0-9]+[hm]', known_args.time_window):
            raise ValueError("Incorrect format for time_window")
        if known_args.time_window[-1]=='h': 
            time_window = datetime.timedelta(hours=int(known_args.time_window[0:-1]))
        else:
            time_window = datetime.timedelta(minutes=int(known_args.time_window[0:-1]))

    baseline_stats = None
    if known_args.baseline_stats_file:
        baseline_stats = load_statistics(known_args.baseline_stats_file)

    schema = load_schema_text(known_args.schema_file)

    logging.log(logging.INFO, "Starting the data analysis pipeline...")
    generate_statistics(
        bq_project_id=known_args.bq_project_id,
        query=known_args.query,
        output_path=known_args.output_path,
        start_time=start_time,
        end_time=end_time,
        schema=schema,
        baseline_stats=baseline_stats,
        time_window=time_window)

