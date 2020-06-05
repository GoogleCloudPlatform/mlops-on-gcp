#!/bin/bash
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

# Deploy drift detector flex template

# Set up a global error handler
err_handler() {
    echo "Error on line: $1"
    echo "Caused by: $2"
    echo "That returned exit status: $3"
    echo "Aborting..."
    exit $3
}

trap 'err_handler "$LINENO" "$BASH_COMMAND" "$?"' ERR

# Check command line parameters
if [[ $# < 2 ]]; then
  echo 'USAGE:  ./deploy_flex_template.sh PROJECT_ID TEMPLATE_LOCATION'
  exit 1
fi

# Set script constants

_PROJECT_ID=${1}
_TEMPLATE_LOCATION=${2}
_TEMPLATE_NAME=log_analyzer


# Set project
echo INFO: Setting the project to: $_PROJECT_ID
gcloud config set project $_PROJECT_ID

# Build drift-detector image
export TEMPLATE_IMAGE="gcr.io/$_PROJECT_ID/$_TEMPLATE_NAME:latest"
gcloud builds submit --tag "$TEMPLATE_IMAGE" .

# Deploy the template
export TEMPLATE_PATH="$_TEMPLATE_LOCATION/$_TEMPLATE_NAME.json"
gcloud beta dataflow flex-template build $TEMPLATE_PATH \
  --image "$TEMPLATE_IMAGE" \
  --sdk-language "PYTHON" \
  --metadata-file "metadata.json"