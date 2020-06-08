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
import datetime
import json
import mock
import pytest
import numpy as np

import tensorflow as tf
from tensorflow_metadata.proto.v0 import schema_pb2
from google.protobuf.json_format import MessageToDict, MessageToJson, ParseDict

from coders.beam_example_coders import InstanceCoder 

schema_dict = {
    'feature': [
        {'name': 'Elevation', 'type': 'FLOAT'},
        {'name': 'Aspect', 'type': 'FLOAT'},
        {'name': 'Slope', 'type': 'FLOAT'},
        {'name': 'Horizontal_Distance_To_Hydrology', 'type': 'FLOAT'},
        {'name': 'Vertical_Distance_To_Hydrology', 'type': 'FLOAT'},
        {'name': 'Horizontal_Distance_To_Roadways', 'type': 'FLOAT'},
        {'name': 'Hillshade_9am', 'type': 'FLOAT'},
        {'name': 'Hillshade_Noon', 'type': 'FLOAT'},
        {'name': 'Hillshade_3pm', 'type': 'FLOAT'},
        {'name': 'Horizontal_Distance_To_Fire_Points', 'type': 'FLOAT'},
        {'name': 'Wilderness_Area', 'type': 'BYTES', 'domain': 'Wilderness_Area'},
        {'name': 'Soil_Type', 'type': 'BYTES', 'domain': 'Soil_Type'}, ],
    'stringDomain': [
        {'name': 'Soil_Type',
        'value': ['2702', '2703', '2704', '2705', '2706', '2717',
                  '3501', '3502', '4201', '4703', '4704', '4744',
                  '4758', '5101', '5151', '6101', '6102', '6731',
                  '7101', '7102', '7103', '7201', '7202', '7700',
                  '7701', '7702', '7709', '7710', '7745', '7746',
                  '7755', '7756', '7757', '7790', '8703', '8707',
                  '8708', '8771', '8772', '8776']},
      {'name': 'Wilderness_Area',
        'value': ['Cache', 'Commanche', 'Neota', 'Rawah']}]}


_log_record_object_format = {
    "model": "covertype_classifier_tf",
    "model_version": "v2",
    "time": datetime.datetime.fromisoformat("2020-05-17T10:20:00"),
    "raw_data": '{"instances": [{"Elevation": [3716, 3717], "Aspect": [336, 337], "Slope": [9, 8], "Horizontal_Distance_To_Hydrology": [1026, 1027], "Vertical_Distance_To_Hydrology": [270, 271], "Horizontal_Distance_To_Roadways": [5309, 5319], "Hillshade_9am": [203, 204], "Hillshade_Noon": [230, 231], "Hillshade_3pm": [166, 167], "Horizontal_Distance_To_Fire_Points": [3455, 3444], "Wilderness_Area": ["Commanche", "Aaaa"], "Soil_Type": ["8776", "9999"]}, {"Elevation": [3225], "Aspect": [326], "Slope": [9], "Horizontal_Distance_To_Hydrology": [342], "Vertical_Distance_To_Hydrology": [0], "Horizontal_Distance_To_Roadways": [5500], "Hillshade_9am": [198], "Hillshade_Noon": [230], "Hillshade_3pm": [172], "Horizontal_Distance_To_Fire_Points": [1725], "Wilderness_Area": ["Rawah"], "Soil_Type": ["7201"]}]}',
    "raw_prediction": '{"predictions": [[4.21827644e-06, 1.45283067e-07, 6.71478847e-21, 4.34945702e-21, 5.18628625e-31, 1.35843754e-22, 0.999995589], [0.948056221, 0.0518435165, 2.80540131e-12, 4.14544565e-14, 8.18011e-10, 1.02051131e-10, 0.000100270954]]}',
    "groundtruth": None
  }

_log_record_list_format = {
    "model": "covertype_classifier_sklearn",
    "model_version": "v2",
    "time": datetime.datetime.fromisoformat("2020-05-17T10:20:00"),
    "raw_data": '{"instances": [[3012, 84, 7, 309, 50, 361, 230, 228, 131, 1205, "Rawah", "7202"], [3058, 181, 16, 42, 10, 1803, 224, 248, 152, 421, "Commanche", "4758"]]}',
    "raw_prediction": '{"predictions": [0, 1, 1]}',
    "groundtruth": None
  }


@pytest.fixture
def coder():
    schema = schema_pb2.Schema()
    ParseDict(schema_dict, schema)

    end_time = datetime.datetime.fromisoformat('2020-05-17T10:30:00')
    time_window = datetime.timedelta(minutes=30)
    slicing_column = 'time_slice'
    
    return InstanceCoder(schema=schema, 
                         end_time=end_time, 
                         time_window=time_window,
                         slicing_column=slicing_column)

def test_get_time_slice(coder):

    time_stamp = '2020-02-17T09:00:01'
    time_slice = coder._get_time_slice(time_stamp)
    expected_result = '2020-02-17T09:00_2020-02-17T09:30' 

    print(time_slice)
    assert time_slice == expected_result


def test_instancecoder_constructor():

    expected_result = {
      'Elevation': np.float, 
      'Aspect': np.float, 
      'Slope': np.float, 
      'Horizontal_Distance_To_Hydrology': np.float, 
      'Vertical_Distance_To_Hydrology':np.float,
      'Horizontal_Distance_To_Roadways': np.float, 
      'Hillshade_9am': np.float,
      'Hillshade_Noon': np.float, 
      'Hillshade_3pm': np.float, 
      'Horizontal_Distance_To_Fire_Points': np.float, 
      'Wilderness_Area': np.str,
      'Soil_Type': np.str}
    
    end_time =  datetime.datetime.fromisoformat('2020-05-17T10:30:00')
    time_window = datetime.timedelta(minutes=30)
    slicing_column='time_slice'
    schema = schema_pb2.Schema()
    ParseDict(schema_dict, schema)
    coder = InstanceCoder(schema=schema, 
                          end_time=end_time,
                          time_window=time_window,
                          slicing_column=slicing_column)
    assert coder._features == expected_result


def test_instancecoder_object(coder):
    examples = coder.process(_log_record_object_format)
    example = next(examples)
    print('/n')
    print(example)
    example = next(examples)
    print('/n')
    print(example)

def test_instancecoder_list(coder):
    examples = coder.process(_log_record_list_format)
    example = next(examples)
    print('/n')
    print(example)
    example = next(examples)
    print('/n')
    print(example)

