import datetime
import os
import subprocess
import argparse
import logging
import os
import sys
import time  
import json

# Upload results
# gcs_model_path = os.path.join('gs://', BUCKET_NAME,
#     datetime.datetime.now().strftime('iris_%Y%m%d_%H%M%S'), model_filename)
# subprocess.check_call(['gsutil', 'cp', model_filename, gcs_model_path],
#     stderr=sys.stdout)

def upload_to_gcs(local, uri):
    pid=subprocess.Popen(['gsutil', '-q', 'cp', local, uri])
    pid.wait()
    logging.info('Uploaded to GCS: %s', uri)

def download_from_gcs(uri, local):
    pid=subprocess.Popen(['gsutil', '-q', 'cp', uri, local])
    pid.wait()
    logging.info('Downloaded from GCS: %s', uri)

def install_package(package):
    pid=subprocess.Popen(['pip3', 'install', '--user', '--upgrade', '--force-reinstall', '--no-deps', package])
    pid.wait()
    logging.info('Installed package: %s', package)

def run_trainer(module, trainer_args):
    pid=subprocess.Popen(['python3', '-m', module] + trainer_args)
    pid.wait()
    logging.info('Training finished: %s', module)

def main():
    # Example parameters
    # --cluster='{"chief": ["127.0.0.1:2222"]}'
    # --task='{"type": "chief", "index": 0}'
    # --job='{ "package_uris": ["gs://x-artifacts/caip-training/training_20200828_151350/packages/4dcbe0be4eda1060c4747/trainer-0.1.tar.gz"],
    #       "python_module": "training.task",
    #       "args": ["--sqlname", "demo:us-central1:mlops1-sql", "--sqlconn", "mysql+pymysql://user:password@127.0.0.1:3306/mlflow", "--mlflowuri", "gs://mlops1-artifacts/experiments", "--epochs", "2"],
    #       "region": "us-central1",
    #       "runtime_version": "2.1",
    #       "job_dir": "gs://mlops1-artifacts/experiments/caip-training/training_20200828_151350",
    #       "run_on_raw_vm": true,
    #       "python_version": "3.7" }'
    logging.info('Arguments: %s',' '.join(sys.argv[1:]))
    parser = argparse.ArgumentParser()
    parser.add_argument('--cluster', type=json.loads)
    parser.add_argument('--task', type=json.loads)
    parser.add_argument('--job', type=json.loads)
    parser.add_argument('--tpu_node', type=json.loads)
    parser.add_argument('--hyperparams', type=json.loads)

    # parser.add_argument('--job-dir', type=str)
    # parser.add_argument('--mlflowuri', type=str)
    # parser.add_argument('--epochs', type=str)
    args = parser.parse_args()

    if not os.path.isdir('mltrainer'):
        os.mkdir('mltrainer')
    os.chdir('mltrainer')

    package_uris = args.job.get('package_uris', [])
    if (not package_uris):
        raise ValueError('Missing package URI. Please provide --package-path during job submit')
    for uri in package_uris:
        local = uri.rsplit('/',1)[-1]
        download_from_gcs(uri,local)
        install_package(local)
    # envvariables = dict(MLFLOW_TRACKING_URI=,MLFLOW_EXPERIMENTS_URI=,MLOPS_REGION=,MLOPS_COMPOSER_NAME=)
    trainer_args=args.job.get('args',[])
    jobdir=args.job.get('job_dir', None)
    if jobdir:
        trainer_args.extend(['--job_dir', args.job.get('job_dir', None)])
    python_module=args.job.get('python_module', None)
    print(f"args: {' '.join(trainer_args)}")
    run_trainer(python_module, trainer_args)

if __name__ == '__main__':
    logging.info('Training main started')
    main()