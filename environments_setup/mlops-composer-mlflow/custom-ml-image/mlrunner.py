# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the \"License\");
# you may not use this file except in compliance with the License.\n",
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an \"AS IS\" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
import subprocess
import argparse
import os
import sys
import time  
import json

def upload_to_gcs(local, uri):
    pid=subprocess.Popen(['gsutil', '-q', 'cp', local, uri])
    pid.wait()
    print('Uploaded from {} to GCS: {}}'.format(local, uri))

def download_from_gcs(uri, local):
    pid=subprocess.Popen(['gsutil', '-q', 'cp', uri, local])
    pid.wait()
    print('Downloaded from GCS: {} to {}'.format(uri, local))

def install_package(package):
    pid=subprocess.Popen(['pip3', 'install', '--user', '--upgrade', '--force-reinstall', '--no-deps', package])
    pid.wait()
    print('Installed package: {}'.format(package))

def run_trainer(module, trainer_args):
    pid=subprocess.Popen(['python3', '-m', module] + trainer_args)
    pid.wait()
    print('Training finished: {}'.format(module))

def main():
    # Example parameters
    #--module_name=training.task 
    #--package_uris=gs://mlops1-artifacts/experiments/caip-training/training_20200828_222445/packages/dae4fdaadf6/trainer-0.1.tar.gz
    #--job-dir=gs://mlops1-artifacts/experiments/caip-training/training_20200828_222445
    #--mlflowuri gs://mlops1-artifacts/experiments
    #--data_source gs://mlops1-training/set1

    print('Arguments: {}'.format(' '.join(sys.argv[1:])))
    parser = argparse.ArgumentParser()
    # GCS folder of training package
    parser.add_argument('--package_uris', type=str)
    # Job result GCS folder output
    parser.add_argument('--job-dir', type=str)
    # Python module name of ML task
    parser.add_argument('--module_name', type=str)
    # MLflow experiments result folder
    parser.add_argument('--mlflowuri', type=str)
    # Data source file URI for training examples
    parser.add_argument('--data_source', type=str)

    args, unknown_args = parser.parse_known_args()

    local_data_dir='/mltrainer/data'
    if not os.path.isdir(local_data_dir):
        os.mkdir(local_data_dir)
    os.chdir(local_data_dir)

    if not args.package_uris:
        raise ValueError('Missing package URI. Please provide --package-path during job submit')

    local = args.package_uris.rsplit('/',1)[-1]
    download_from_gcs(args.package_uris, local)
    install_package(local)

    if args.data_source:
        download_from_gcs(args.data_source, local_data_dir)
        sys.argv.append('--local_data')
        sys.argv.append(local_data_dir)
    run_trainer(args.module_name, sys.argv[1:])

if __name__ == '__main__':
    print('ML runner started')
    main()
