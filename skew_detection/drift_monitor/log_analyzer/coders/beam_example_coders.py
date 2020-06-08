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

"""A DoFn converting a raw_data field in AI Platform Prediction
request-response log into tfdv.types.BeamExample.
"""


import json
import apache_beam as beam
import numpy as np

from datetime import datetime, timedelta
from typing import List, Optional, Text, Union, Dict, Iterable, Mapping
from tensorflow_data_validation import types
from tensorflow_data_validation import constants
from tensorflow_metadata.proto.v0 import schema_pb2

_RAW_DATA_COLUMN = 'raw_data'
_INSTANCES_KEY = 'instances'
_TIMESTAMP_KEY = 'time'

_SCHEMA_TO_NUMPY = {
    schema_pb2.FeatureType.BYTES:  np.str,
    schema_pb2.FeatureType.INT: np.int64,
    schema_pb2.FeatureType.FLOAT: np.float
}


@beam.typehints.with_input_types(Dict)
@beam.typehints.with_output_types(types.BeamExample)
class InstanceCoder(beam.DoFn):
    """A DoFn which converts an AI Platform Prediction request body to
    types.BeamExample elements."""

    def __init__(self, 
        schema: schema_pb2, 
        end_time: datetime=None, 
        time_window: datetime=None,
        slicing_column: str=None):

        self._example_size = beam.metrics.Metrics.counter(
            constants.METRICS_NAMESPACE, "example_size")

        self._features = {}
        for feature in schema.feature:
            if not feature.type in _SCHEMA_TO_NUMPY.keys():
                raise ValueError(
                    "Unsupported feature type: {}".format(feature.type))
            self._features[feature.name] = _SCHEMA_TO_NUMPY[feature.type]

        if end_time and time_window and slicing_column:
            self._end_time = end_time
            self._time_window = time_window
            self._slicing_column = slicing_column 
        else:
            self._slicing_column = None

    def _get_time_slice(self, time_stamp: str) -> str:
        """
        Assigns a time stamp to a time slice.

        Args:
            time_stamp: A date_time string in the ISO YYYY-MM-DDTHH:MM:SS format
        Returns:
            A time slice as a string in the following format:
            YYYY-MM-DDTHH:MM_YYYY-MM-DDTHH:MM
        """

        time_stamp = datetime.strptime(time_stamp, '%Y-%m-%dT%H:%M:%S')

        q = (self._end_time - time_stamp) // self._time_window
        slice_end = self._end_time - q * self._time_window
        slice_begining = self._end_time - (q + 1) * self._time_window

        return (slice_begining.strftime('%Y-%m-%dT%H:%M') + '_' +
                slice_end.strftime('%Y-%m-%dT%H:%M'))

    def _parse_raw_instance(self, raw_instance: Union[list, dict]) -> dict:
        if type(raw_instance) is dict:
            instance = {name: np.array(value if type(value) == list else [value], dtype=self._features[name])
                        for name, value in raw_instance.items()}
        elif type(raw_instance) is list:
            instance = {name: np.array([value], dtype=self._features[name])
                        for name, value in zip(list(self._features.keys()), raw_instance)}
        else:
            raise TypeError(
                "Unsupported input instance format. Only JSON list or JSON object instances are supported")

        return instance

    def process(self, log_record: Dict) -> Iterable:

        raw_data = json.loads(log_record[_RAW_DATA_COLUMN])

        for raw_instance in raw_data[_INSTANCES_KEY]:
            instance = self._parse_raw_instance(raw_instance)
            if self._slicing_column:
                instance[self._slicing_column] = np.array(
                    [self._get_time_slice(log_record[_TIMESTAMP_KEY])])
            yield instance
