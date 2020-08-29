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

import pytest

from locust.env import Environment
from locust import User, task, between, events

import tasks
from tasks import AIPPUser, on_test_start, on_test_stop

LOCUST_TEST_BUCKET=''
LOCUST_TEST_DATA='test-config/test-payload.json'
LOCUST_TEST_CONFIG='test-config/test-config.json'

@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv('LOCUST_TEST_BUCKET')
    monkeypatch.setenv('LOCUST_TEST_DATA', 'locust-test/test-payload.json')
    monkeypatch.setenv('LOCUST_TEST_CONFIG', 'locust-test/test-config.json')

@pytest.fixture
def environment():
    
    environment = Environment()
    
    return environment

def test_on_start(environment):
    
    user1 = AIPPUser(environment)
    user1.on_start()
    print(len(user1.tasks))
    
def test_execute_task(environment):
    
    user1 = AIPPUser(environment)
    user1.on_start()
    user1.tasks[0](user1)
 
    
def test_on_test_start():
    on_test_start()
    on_test_stop()
    on_test_stop()
    on_test_start()
    on_test_stop()
    