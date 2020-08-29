#!/usr/bin/env python

# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
An example locustfile demonstrating how to load test 
an AI Platform Prediction predict endpoint.
"""

import inspect
import json
import logging
import os
import random
import time

import gevent

from functools import partial
from datetime import datetime
from functools import wraps

import google.auth
import google.auth.transport.requests

from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from google.api_core.exceptions import RetryError
from google.auth.transport.requests import AuthorizedSession
from google.cloud.logging_v2 import LoggingServiceV2Client
from google.cloud.logging_v2.types import LogEntry
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.struct_pb2 import Struct

from locust import User, task, between, events
from locust.runners import MasterRunner, WorkerRunner, LocalRunner
from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, STATE_RUNNING


LOG_STATS_INTERVAL_SEC = 5
LOG_NAME = 'locust'

TEST_BUCKET_ENV = 'LOCUST_TEST_BUCKET'
TEST_PAYLOAD_ENV= 'LOCUST_TEST_PAYLOAD'
TEST_CONFIG_ENV = 'LOCUST_TEST_CONFIG'


def greenlet_exception_handler():
    """
    Returns a function that can be used as an argument to Greenlet.link_exception() to capture
    unhandled exceptions.
    """
    def exception_handler(greenlet):
        logging.error("Unhandled exception in greenlet: %s", greenlet,
                      exc_info=greenlet.exc_info)
        global unhandled_greenlet_exception
        unhandled_greenlet_exception = True
    return exception_handler


def log_stats(environment):
    """
    Logs current test stats to Cloud Logging.
    
    This function is executed as a greenlet.
    """
    
    global test_id
    test_id = None
    
    logging.info('Entering the Cloud Logging logger greenlet')
    
    creds, project_id = google.auth.default()
    client = LoggingServiceV2Client(credentials=creds)
    project_path = client.project_path(project_id)
    
    while True:
        gevent.sleep(LOG_STATS_INTERVAL_SEC)
        
        if not environment.runner.state in [STATE_RUNNING] or not test_id:
            continue
            
        log_path = client.log_path(project_id, LOG_NAME)             
        timestamp = Timestamp()
        timestamp.FromDatetime(datetime.now())   
        log_entries = []
        for key in sorted(environment.stats.entries.keys()):
            
            r = environment.stats.entries[key]
            payload = Struct()
            payload.update({
                'test_id': test_id,
                'signature': r.name,
                'model': r.method,
                'latency': r.get_current_response_time_percentile(0.95),
                'user_count': environment.runner.user_count,
                'num_requests': environment.runner.stats.total.num_requests,
                'num_failures': environment.runner.stats.total.num_failures,
            })
            
            log_entry = LogEntry(
                log_name=log_path,
                resource={'type': 'global'},
                timestamp=timestamp,
                json_payload=payload
            )
            log_entries.append(log_entry)
  
        if log_entries:
            try:
                response = client.write_log_entries(
                    entries=log_entries)
            except GoogleAPICallError as e: 
                logging.error('GoogleAPICallError: %s', e.message)
            except RetryError:
                logging.error('RetryError')
            except:
                logging.error('Unknow exception')
                                       
    
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Intializes Locust process.
    """
    
    # Start the Cloud Logging greenlet on the master 
    if isinstance(environment.runner, MasterRunner):
        logging.info("Starting the master pod.")
        gevent.spawn(log_stats, 
                environment).link_exception(greenlet_exception_handler())
        logging.info("Spawned the Cloud Monitoring logger.")
            
        
@events.test_start.add_listener
def on_test_start(**kwargs):

    global test_id
    
    # Read the test config file and set the test_id global variable
    client = storage.Client()
    bucket = client.get_bucket(os.getenv(TEST_BUCKET_ENV))
    blob = storage.Blob(os.getenv(TEST_CONFIG_ENV), bucket)
    test_id = json.loads(blob.download_as_string())['test_id']    
    
    
@events.test_stop.add_listener
def on_test_stop(**kwargs):
    global test_id
    test_id = None


class AIPPClient(object):
    """
    A convenience wrapper around AI Platform Prediction REST API.
    """
    
    def __init__(self, service_endpoint):
        logging.info(
            "Setting the AI Platform Prediction service endpoint: {}".format(
                service_endpoint))
        credentials, _ = google.auth.default()
        self._authed_session = AuthorizedSession(credentials)
        self._service_endpoint = service_endpoint
    
    def predict(self, project_id, model, version, signature, instances):
        """
        Invokes the predict method on the specified signature.
        """
        
        url = '{}/v1/projects/{}/models/{}/versions/{}:predict'.format(
            self._service_endpoint, project_id, model, version)
            
        request_body = {
            'signature_name': signature,
            'instances': instances
        }
    
        response = self._authed_session.post(url, data=json.dumps(request_body))
        return response
 

def predict_task(
        user:object, 
        project_id:str, 
        model:str, 
        version:str, 
        signature:str,
        instances: dict):
    """
    Calls a predict method on AIPP endpoint and tracks
    the response latency and status with Locust.
    """

    start_time = time.time()
    model_deployment_name = '{}-{}'.format(model,version)
    try:
        response = user.client.predict(
            project_id=project_id,
            model=model,
            version=version,
            signature=signature,
            instances=instances
        )
    except Exception as e:
        total_time = int((time.time() - start_time) * 1000)
        events.request_failure.fire(
                request_type=model_deployment_name,
                name=signature,
                response_time=total_time,
                response_length=0,
                exception=e)
    else:
        total_time = int((time.time() - start_time) * 1000)
        if 'error' in response.json():
            events.request_failure.fire(
                    request_type=model_deployment_name,
                    name=signature,
                    response_time=total_time,
                    response_length=len(response.text),
                    exception=response.text)
        else:
            events.request_success.fire(
                    request_type=model_deployment_name,
                    name=signature,
                    response_time=total_time,
                    response_length = len(response.text))
       
        
class AIPPUser(User):
    """
    A class simulating calls to AI Platform Prediction.
    """
    
    wait_time = between(1, 2)
    test_data = None
    test_config = None
    
    def __init__(self, *args, **kwargs):
        super(AIPPUser, self).__init__(*args, **kwargs) 
        self.client = AIPPClient(self.environment.host)

    def on_start(self):
        if not AIPPUser.test_data:
            bucket = os.getenv(TEST_BUCKET_ENV)
            config_blob = os.getenv(TEST_CONFIG_ENV)
            test_data_blob = os.getenv(TEST_PAYLOAD_ENV)
            client = storage.Client()
            bucket = client.get_bucket(bucket)
            blob = storage.Blob(config_blob, bucket)
            AIPPUser.test_config = json.loads(blob.download_as_string())
            blob = storage.Blob(test_data_blob, bucket)
            AIPPUser.test_data = json.loads(blob.download_as_string())
        
        self.tasks.clear()
        for test_instance in AIPPUser.test_data:          
            task = partial(predict_task,
                            project_id=AIPPUser.test_config['project_id'],
                            model=AIPPUser.test_config['model'],
                            version=AIPPUser.test_config['version'],
                            signature=test_instance['signature'],
                            instances=test_instance['instances']
                            )
                
            self.tasks.append(task)

    def on_stop(self):
        AIPPUser.test_data = None
        AIPPUser.test_config = None
        self.tasks.clear()
                    
            
