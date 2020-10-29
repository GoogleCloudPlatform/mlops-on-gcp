# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""

USAGE:

For json data (non-binary), data is generated from script:

python get_request_body_simple.py -m simple

For binary data, you can replace the mug.jpg file with your own jpg:

python get_request_body_simple.py -m image -f mug.jpg

curl -X GET -k -H "Content-Type: application/json" \
    -H "Authorization: Bearer `gcloud auth print-access-token`" \
    "${ENDPOINT}/projects/${PROJECT_NAME}/models/${MODEL_NAME}"

curl \
-X POST localhost:8000/v2/models/simple/infer \
-k -H "Content-Type: application/json" \
-d @simple.json

expected output: {"id":"0","model_name":"simple","model_version":"1","outputs":[{"name":"OUTPUT0","datatype":"INT32","shape":[1,16],"data":[-1,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14]},{"name":"OUTPUT1","datatype":"INT32","shape":[1,16],"data":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]}]}%  

curl \
-X POST ${ENDPOINT}/projects/${PROJECT_NAME}/models/${MODEL_NAME}/versions/v5:predict \
-k -H "Content-Type: application/json" \
-H "Authorization: Bearer `gcloud auth print-access-token`" \
-d @payload.json

binary query below not working due to need of header:

curl \
-X POST localhost:8000/v2/models/resnet50_netdef/infer \
-k -H "Content-Type: application/octet-stream" \
-H "Inference-Header-Content-Length: 138" \
--data-binary "@payload.dat"

curl \
-X POST ${ENDPOINT}/projects/${PROJECT_NAME}/models/${MODEL_NAME}/versions/v3:predict \
-k -H "Content-Type: application/octet-stream" \
-H "Authorization: Bearer `gcloud auth print-access-token`" \
-H "Inference-Header-Content-Length: 135" \
--data-binary "@payload.dat"
"""

from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
import argparse
import numpy as np
import sys
import os
from PIL import Image
import json
import struct

class InferInput:
    """An object of InferInput class is used to describe
    input tensor for an inference request.

    Parameters
    ----------
    name : str
        The name of input whose data will be described by this object
    shape : list
        The shape of the associated input.
    datatype : str
        The datatype of the associated input.
    """

    def __init__(self, name, shape, datatype):
        self._name = name
        self._shape = shape
        self._datatype = datatype
        self._parameters = {}
        self._data = None
        self._raw_data = None

    def set_data_from_numpy(self, input_tensor, binary_data=True):
        """Set the tensor data from the specified numpy array for
        input associated with this object.

        Parameters
        ----------
        input_tensor : numpy array
            The tensor data in numpy array format
        binary_data : bool
            Indicates whether to set data for the input in binary format
            or explicit tensor within JSON. The default value is True,
            which means the data will be delivered as binary data in the
            HTTP body after the JSON object.

        Raises
        ------
        InferenceServerException
            If failed to set data for the tensor.
        """
        self._parameters.pop('shared_memory_region', None)
        self._parameters.pop('shared_memory_byte_size', None)
        self._parameters.pop('shared_memory_offset', None)

        if not binary_data:
            self._parameters.pop('binary_data_size', None)
            self._raw_data = None
            if self._datatype == "BYTES":
                self._data = [val for val in input_tensor.flatten()]
            else:
                self._data = [val.item() for val in input_tensor.flatten()]
        else:
            self._data = None
            if self._datatype == "BYTES":
                self._raw_data = serialize_byte_tensor(input_tensor).tobytes()
            else:
                self._raw_data = input_tensor.tobytes()
            self._parameters['binary_data_size'] = len(self._raw_data)

    def _get_binary_data(self):
        """Returns the raw binary data if available

        Returns
        -------
        bytes
            The raw data for the input tensor
        """
        return self._raw_data

    def _get_tensor(self):
        """Retrieve the underlying input as json dict.

        Returns
        -------
        dict
            The underlying tensor specification as dict
        """
        if self._parameters.get('shared_memory_region') is not None or \
                self._raw_data is not None:
            return {
                'name': self._name,
                'shape': self._shape,
                'datatype': self._datatype,
                'parameters': self._parameters,
            }
        else:
            return {
                'name': self._name,
                'shape': self._shape,
                'datatype': self._datatype,
                'parameters': self._parameters,
                'data': self._data
            }

def serialize_byte_tensor(input_tensor):
    """
        Serializes a bytes tensor into a flat numpy array of length prepend bytes.
        Can pass bytes tensor as numpy array of bytes with dtype of np.bytes_,
        numpy strings with dtype of np.str_ or python strings with dtype of np.object.

        Parameters
        ----------
        input_tensor : np.array
            The bytes tensor to serialize.

        Returns
        -------
        serialized_bytes_tensor : np.array
            The 1-D numpy array of type uint8 containing the serialized bytes in 'C' order.

        Raises
        ------
        InferenceServerException
            If unable to serialize the given tensor.
        """

    if input_tensor.size == 0:
        return np.empty([0])

    # If the input is a tensor of string/bytes objects, then must flatten those into
    # a 1-dimensional array containing the 4-byte byte size followed by the
    # actual element bytes. All elements are concatenated together in "C"
    # order.
    if (input_tensor.dtype == np.object) or (input_tensor.dtype.type == np.bytes_):
        flattened = bytes()
        for obj in np.nditer(input_tensor, flags=["refs_ok"], order='C'):
            # If directly passing bytes to BYTES type,
            # don't convert it to str as Python will encode the
            # bytes which may distort the meaning
            if obj.dtype.type == np.bytes_:
                if type(obj.item()) == bytes:
                    s = obj.item()
                else:
                    s = bytes(obj)
            else:
                s = str(obj).encode('utf-8')
            flattened += struct.pack("<I", len(s))
            flattened += s
        flattened_array = np.asarray(flattened)
        if not flattened_array.flags['C_CONTIGUOUS']:
            flattened_array = np.ascontiguousarray(flattened_array)
        return flattened_array
    return None

def np_to_triton_dtype(np_dtype):
    if np_dtype == np.bool:
        return "BOOL"
    elif np_dtype == np.int8:
        return "INT8"
    elif np_dtype == np.int16:
        return "INT16"
    elif np_dtype == np.int32:
        return "INT32"
    elif np_dtype == np.int64:
        return "INT64"
    elif np_dtype == np.uint8:
        return "UINT8"
    elif np_dtype == np.uint16:
        return "UINT16"
    elif np_dtype == np.uint32:
        return "UINT32"
    elif np_dtype == np.uint64:
        return "UINT64"
    elif np_dtype == np.float16:
        return "FP16"
    elif np_dtype == np.float32:
        return "FP32"
    elif np_dtype == np.float64:
        return "FP64"
    elif np_dtype == np.object or np_dtype.type == np.bytes_:
        return "BYTES"
    return None

def get_inference_request(inputs, request_id):
    infer_request = {}
    if request_id != "":
        infer_request['id'] = request_id
    infer_request['inputs'] = [
        this_input._get_tensor() for this_input in inputs
    ]
    request_body = json.dumps(infer_request)
    json_size = len(request_body)
    binary_data = None
    for input_tensor in inputs:
        raw_data = input_tensor._get_binary_data()
        if raw_data is not None:
            if binary_data is not None:
                binary_data += raw_data
            else:
                binary_data = raw_data

    if binary_data is not None:
        request_body = struct.pack(
            '{}s{}s'.format(len(request_body), len(binary_data)),
            request_body.encode(), binary_data)
        return request_body, json_size

    return infer_request, request_body, None

def preprocess(img, format, dtype, c, h, w, scaling, protocol):
    """
    Pre-process an image to meet the size, type and format
    requirements specified by the parameters.
    """
    if c == 1:
        sample_img = img.convert('L')
    else:
        sample_img = img.convert('RGB')

    resized_img = sample_img.resize((w, h), Image.BILINEAR)
    resized = np.array(resized_img)
    if resized.ndim == 2:
        resized = resized[:, :, np.newaxis]
    
    typed = resized.astype(dtype)

    if scaling == 'INCEPTION':
        scaled = (typed / 128) - 1
    elif scaling == 'VGG':
        if c == 1:
            scaled = typed - np.asarray((128,), dtype=dtype)
        else:
            scaled = typed - np.asarray((123, 117, 104), dtype=dtype)
    else:
        scaled = typed

    # Swap to CHW if necessary
    if format == "FORMAT_NCHW":
        ordered = np.transpose(scaled, (2, 0, 1))
    else:
        ordered = scaled

    return ordered

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m',
                        '--mode',
                        required=False,
                        default=False,
                        help='image or simple')    
    parser.add_argument('-f',
                        '--image_filename', 
                        type=str, default=False,
                        help='Input image / Input folder.')
    FLAGS = parser.parse_args()
    
    if FLAGS.mode == 'image':
        input_name, output_name, c, h, w, format, dtype = 'gpu_0/data', 'gpu_0/softmax', 3, 224, 224, 'FORMAT_NCHW', np.float32
        filenames = []
        if os.path.isdir(FLAGS.image_filename):
            filenames = [
                os.path.join(FLAGS.image_filename, f)
                for f in os.listdir(FLAGS.image_filename)
                if os.path.isfile(os.path.join(FLAGS.image_filename, f))
            ]
        else:
            filenames = [
                FLAGS.image_filename,
            ]
        
        filenames.sort()

        # Preprocess the images into input data according to model
        image_inputs = []
        for filename in filenames:
            img = Image.open(filename)
            image_inputs.append(InferInput(input_name, [1, c, h, w], np_to_triton_dtype(dtype)))
            print(preprocess(img, format, dtype, c, h, w,
                                        'INCEPTION','caip').shape)
            image_inputs[-1].set_data_from_numpy(preprocess(img, format, dtype, c, h, w,
                                        'INCEPTION','caip'))
        request_body, json_size = get_inference_request(image_inputs, '0')
        print("Add Header: Inference-Header-Content-Length: {}".format(json_size))
        uri = "/v2/models/resnet50_netdef/infer"
        with open('payload.dat', 'wb') as output_file:
            output_file.write(request_body)
            output_file.close() 
    else:
        input0_data = np.arange(start=0, stop=16, dtype=np.int32)
        input0_data = np.expand_dims(input0_data, axis=0)
        input1_data = np.full(shape=(1, 16), fill_value=-1, dtype=np.int32)
        inputs = []
        inputs.append(InferInput('INPUT0', [1, 16], "INT32"))
        inputs.append(InferInput('INPUT1', [1, 16], "INT32"))
        inputs[0].set_data_from_numpy(input0_data, binary_data=False)
        inputs[1].set_data_from_numpy(input1_data, binary_data=False)    
        query_params = {'test_1': 1, 'test_2': 2 }
        infer_request, request_body, json_size = get_inference_request(inputs, '0')
        uri = "/v2/models/simple/infer"
        with open('simple.json', 'w') as output_file:
            json.dump(infer_request, output_file)

    
