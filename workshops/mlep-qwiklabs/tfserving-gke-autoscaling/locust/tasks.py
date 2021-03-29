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
an TF Serving endpoint.
"""

import json
import logging
import math
import os

import locust


TEST_REQUEST_BODY = 'request-body.json'
TEST_CONFIG = 'test-config.json'

class StepLoad(locust.LoadTestShape):
    """
    The load shape class that progressively adds users up to the maximum.
    After the maximum load has been reached the class starts to progressively decrease 
    the load till all users are stopped.
    """

    max_steps = 11
    step_time = 60
    step_load = 2
    spawn_rate = 1

    def tick(self):
        run_time = self.get_run_time()

        current_step = math.floor(run_time / self.step_time) + 1

        if current_step <= self.max_steps:
            return (current_step * self.step_load, self.spawn_rate)
        else:
            return None



class TFServingClient(locust.HttpUser):
    """
    Simulated TF Serving client.
    """

    wait_time = locust.between(0.8, 0.9)

    @locust.task
    def predict(self):
            
        response =self.client.post(self.url,
                                   data=json.dumps(self.request_body))

        if 'error' in response.json():
            self.environment.runner.stats.log_error(
                response.request.method,
                response.request.path_url)
        
    def on_start(self):
        with open(TEST_CONFIG) as f:
            test_config = json.load(f)
        with open(TEST_REQUEST_BODY) as f:
            self.request_body = json.load(f)

        self.url = '{}/v1/models/{}/versions/{}:predict'.format(
            self.environment.host, 
            test_config['model'],
            test_config['version'])

        
