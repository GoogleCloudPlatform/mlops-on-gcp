# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from locust import HttpUser, task, between
from locust import LoadTestShape
import json
from math import sin, pi

class ProfileLoad(LoadTestShape):
    '''
    This load profile starts at 0 and steps up by step_users
    increments every tick, up to target_users.  After reaching
    target_user level, load will stay at target_user level
    until time_limit is reached.
    '''

    target_users   = 70
    step_users     = 5      # ramp users each step
    time_limit     = 3600   # seconds

    def tick(self):
        num_steps = self.target_users/self.step_users
        run_time = round(self.get_run_time())

        if run_time < self.time_limit:
            if num_steps < run_time:
                user_count = num_steps * self.step_users
            else:
                user_count = self.target_users
            return (user_count,self.step_users)
        else:
            return None

class TritonUser(HttpUser):
    wait_time = between(1, 1)

    @task
    def bert_disconnect(self):
        response = self.client.post(self.url1, headers=self.headers, data=json.dumps(self.data))

    @task(3)
    def bert(self):
        response = self.client.post(self.url1, data=json.dumps(self.data))
    
    def on_start(self):
        with open('bert_request.json') as f:
            self.data = json.load(f)

        self.url1 = '{}/v2/models/{}/infer'.format(
            self.environment.host,
            'bert-tier1')

        self.headers = {'Connection': 'close'}

