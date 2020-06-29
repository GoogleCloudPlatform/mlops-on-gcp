#!/bin/bash
# Copyright 2019 Google Inc. All Rights Reserved.
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

# Destroy the KFP environment

# Verify command line parameters
if [[ $# < 1 ]]; then
  echo 'USAGE:  ./destroy.sh PROJECT_ID [NAME_PREFIX=PROJECT_ID] [REGION=us-central1] [ZONE=us-central1-a]'
  exit 1
fi

PROJECT_ID=${1}
NAME_PREFIX=${2:-$PROJECT_ID}
REGION=${3:-us-central1} 
ZONE=${4:-us-central1-a}

# Destroy the Terraform configuration
echo INFO: Starting Terraform destroy
pushd terraform
terraform destroy \
-var "project_id=$PROJECT_ID" \
-var "region=$REGION" \
-var "zone=$ZONE" \
-var "name_prefix=$NAME_PREFIX" 
popd
