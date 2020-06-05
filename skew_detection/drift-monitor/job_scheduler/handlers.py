# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper routines to trigger runs of the drift detector Dataflow template. """


import argparse
import click
import datetime
import time
import json
import googleapiclient.discovery
import logging

from typing import List, Optional, Text, Union, Dict
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2


_SCHEMA_FILE_PATH = './setup.py'
_JOB_NAME_PREFIX = 'log-analyzer'

def _prepare_log_analyzer_request_body(
    job_name: Text,
    template_path: Text,
    model: Text,
    version: Text,
    log_table: Text,
    start_time: Text ,
    end_time: Text,
    output_location: Text,
    schema_location: Text,
    baseline_stats_location: Text,
    time_window: Text
) -> Dict:
    """Prepares a body of the log analyzer Dataflow template run request."""

    parameters = {
        'request_response_log_table': log_table,
        'model': model,
        'version': version,
        'start_time': start_time,
        'end_time': end_time,
        'output_path': output_location,
        'schema_file': schema_location
    }

    if baseline_stats_location:
        parameters['baseline_stats_file'] = baseline_stats_location 
    
    if time_window:
        parameters['time_window'] = time_window
    
    body = {
        'launch_parameter': 
            {
                'jobName': job_name,
                'parameters' : parameters,
                'containerSpecGcsPath': template_path
            }}

    return body
    
def run_log_analyzer(
    project_id: Text,
    region: Text,
    template_path: Text,
    model: Text,
    version: Text,
    log_table: Text,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    output_location: Text,
    schema_location: Text,
    baseline_stats_location: Optional[Text]=None,
    time_window: Optional[Text]=None
) -> Dict:
    """Runs the log analyzer Dataflow template."""

    service = googleapiclient.discovery.build('dataflow', 'v1b3')

    time_stamp = time.strftime("%Y%m%d-%H%M%S")
    job_name = '{}-{}'.format(_JOB_NAME_PREFIX, time_stamp)
    start_time = start_time.isoformat(sep='T', timespec='seconds')
    end_time = end_time.isoformat(sep='T', timespec='seconds')
    output_location = '{}/{}_{}_{}'.format(output_location, time_stamp, start_time, end_time)

    body = _prepare_log_analyzer_request_body(
        job_name=job_name,
        template_path=template_path,
        model=model,
        version=version,
        log_table=log_table,
        start_time=start_time,
        end_time=end_time,
        output_location=output_location,
        schema_location=schema_location,
        baseline_stats_location=baseline_stats_location,
        time_window=time_window
    )

    request = service.projects().locations().flexTemplates().launch(
        location=region,
        projectId=project_id,
        body=body)

    response = request.execute()

    return response


def schedule_log_analyzer(
    task_queue: Text,
    service_account: Text,
    schedule_time: datetime.datetime,
    project_id: Text,
    region: Text,
    template_path: Text,
    model: Text,
    version: Text,
    log_table: Text,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    output_location: Text,
    schema_location: Text,
    baseline_stats_location: Optional[Text]=None,
    time_window: Optional[Text]=None
) -> Dict:
    """Creates a Cloud Task that submits a run of the log analyzer template."""

    service_uri = 'https://dataflow.googleapis.com/v1b3/projects/{}/locations/{}/flexTemplates:launch'.format(
        project_id, region)

    time_stamp = time.strftime("%Y%m%d-%H%M%S")
    job_name = '{}-{}'.format(_JOB_NAME_PREFIX, time_stamp)
    start_time = start_time.isoformat(sep='T', timespec='seconds')
    end_time = end_time.isoformat(sep='T', timespec='seconds')
    output_location = '{}/{}_{}_{}'.format(output_location, time_stamp, start_time, end_time)

    body = _prepare_log_analyzer_request_body(
        job_name=job_name,
        template_path=template_path,
        model=model,
        version=version,
        log_table=log_table,
        start_time=start_time,
        end_time=end_time,
        output_location=output_location,
        schema_location=schema_location,
        baseline_stats_location=baseline_stats_location,
        time_window=time_window
    )

    task = {
        'http_request': {
            'http_method': 'POST',
            'url': service_uri,
            'body': json.dumps(body).encode(),
            'headers': {'content-type': 'application/json'},
            'oauth_token': {'service_account_email': service_account}
        }
    }
    
    timestamp = timestamp_pb2.Timestamp()
    timestamp.FromDatetime(schedule_time)
    task['schedule_time'] = timestamp

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(project_id, region, task_queue)
    response = client.create_task(parent, task)

    return response

