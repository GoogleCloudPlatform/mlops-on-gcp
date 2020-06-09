# Managing Log Analyzer jobs

This folder contains a simple CLI - `dms` - designed to facilitate triggering and scheduling of the Log Analyzer jobs.

The `dms` utility supports two commands: 
- `run` - The `run` command triggers an immediate run of the Log Analyzer template
- `schedule` - The `schedule` command allows you to schedule a run of the Log Analyzer template in future. 

## Installing the `dms` utility

To install the utility, execute `pip install --editable .` from the `/skew_detection/drift_monitor/job_scheduler` folder.

## Triggering Log Analyzer jobs 

You can use the `dms run` command to trigger a run of the Log Analyzer template. The Log Analyzer job will start immediately. You will be able to monitor the job using [Dataflow Jobs](https://console.cloud.google.com/dataflow)

Use `dms run --help` for the detailed list of runtime parameters.

## Scheduling Log Analyzer jobs

The `dms schedule` command allows you to schedule a Log Analyzer job to be executed in the future. [**Cloud Tasks**](https://cloud.google.com/tasks) is used to manage scheduling and execution of the job. Before using the `dms schedule` command you need to set up a **Cloud Tasks** queue and a service account to be used to invoke the Dataflow Flex Templates service.

### Creating a Cloud Tasks queue
### Creating a Cloud Tasks service account
### Scheduling a Log Analyzer job
