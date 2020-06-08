# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A command line interface to trigger and schedule log analyzer runs.  """

import click
import datetime
import logging

from handlers import run_log_analyzer
from handlers import schedule_log_analyzer


@click.group()
def cli():
    pass

@cli.command()
@click.option('--template_path', envvar='DM_TEMPLATE_PATH', help='A GCS path to log analyzer flex template', required=True)
@click.option('--project', envvar='DM_PROJECT_ID', help='A GCP project ID', required=True)
@click.option('--region', envvar='DM_REGION', help='A GCP region', required=True)
@click.option('--log_table', envvar='DM_LOG_TABLE', help='A full name of the request_response log table', required=True)
@click.option('--model', envvar='DM_MODEL', help='An AI Platform Prediction model', required=True)
@click.option('--version', envvar='DM_VERSION', help='An AI Platform Prediction version', required=True)
@click.option('--start_time', envvar='DM_START_TIME', help='The beginning of a time window in the log table (UTC time).', required=True, type=click.DateTime())
@click.option('--end_time', envvar='DM_END_TIME', help='The end of a time window in the log table (UTC time).', required=True, type=click.DateTime())
@click.option('--output', envvar='DM_OUTPUT', help='A GCS location for the output statistics and anomalies files', required=True)
@click.option('--schema',  envvar='DM_SCHEMA', help='A GCS location of the schema file', required=True)
@click.option('--baseline_stats', envvar='DM_STATS', help='A GCS location of the baseline stats file')
@click.option('--time_window', envvar='DM_TIME_WINDOW', help='A time window for slice calculations')
def run(template_path, model, version, project, region, log_table, start_time,
    end_time, output, schema, baseline_stats, time_window):

    response = run_log_analyzer(
        project_id=project,
        region=region,
        template_path=template_path,
        model=model,
        version=version,
        log_table=log_table,
        start_time=start_time,
        end_time=end_time,
        output_location=output,
        schema_location=schema,
        baseline_stats_location=baseline_stats,
        time_window=time_window
    )
    print("Submitted a log analyzer template run: DataFlow Job ID={}".format(
        response['job']['id'])) 

@cli.command()
@click.option('--template_path', envvar='DM_TEMPLATE_PATH', help='A GCS path to the log analyzer flex template', required=True)
@click.option('--execute_time', envvar='DM_EXECUTE_TIME', help='The log analyzer template will be triggered at this time', required=True, type=click.DateTime())
@click.option('--queue', envvar='DM_QUEUE', help='A Cloud Tasks queue to use for scheduling', required=True)
@click.option('--account', envvar='DM_ACCOUNT', help='An email address of a service account to use for scheduling', required=True)
@click.option('--project', envvar='DM_PROJECT_ID', help='A GCP project ID', required=True)
@click.option('--region', envvar='DM_REGION', help='A GCP region', required=True)
@click.option('--log_table', envvar='DM_LOG_TABLE', help='A full name of the request_response log table', required=True)
@click.option('--model', envvar='DM_MODEL', help='An AI Platform Prediction model', required=True)
@click.option('--version', envvar='DM_VERSION', help='An AI Platform Prediction version', required=True)
@click.option('--start_time', envvar='DM_START_TIME', help='The beginning of a time window in the log table (UTC time).', required=True, type=click.DateTime())
@click.option('--end_time', envvar='DM_END_TIME', help='The end of a time window in the log table (UTC time).', required=True, type=click.DateTime())
@click.option('--output', envvar='DM_OUTPUT', help='A GCS location for the output statistics and anomalies files', required=True)
@click.option('--schema',  envvar='DM_SCHEMA', help='A GCS location of the schema file', required=True)
@click.option('--baseline_stats', envvar='DM_STATS', help='A GCS location of the baseline stats file')
@click.option('--time_window', envvar='DM_TIME_WINDOW', help='A time window for slice calculations')
def schedule(template_path, model, version, queue, account, execute_time, project,
    region, log_table, start_time, end_time, output, schema, baseline_stats, time_window):

    response = schedule_log_analyzer(
        task_queue=queue,
        service_account=account,
        schedule_time=execute_time,
        project_id=project,
        region=region,
        template_path=template_path,
        model=model,
        version=version,
        log_table=log_table,
        start_time=start_time,
        end_time=end_time,
        output_location=output,
        schema_location=schema,
        baseline_stats_location=baseline_stats,
        time_window=time_window
    ) 

    print("Scheduled the log analyzer template to run at: {}".format( execute_time)) 

if __name__ == '__main__':
    cli()