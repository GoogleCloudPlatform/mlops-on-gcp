# Scheduling Log Analyzer runs

This folder contains a simple CLI - `dms` - designed to facilitate triggering and scheduling of the Log Analyzer runs.

The `dms` utility supports two commands: 
- `run` - The `run` command triggers an immediate run of the Log Analyzer template
- `schedule` - The `schedule` command allows you to schedule a run of the Log Analyzer template in future. 

## Installing the `dms` utility

To install the utility, execute `pip install --editable .` from the `/skew_detection/drift_monitor/job_scheduler` folder.

## Triggering runs 

You can use `dms run` to trigger a run of the Log Analyzer template. The Log Analyzer job will start immediately. You will be able to monitor the job using [Dataflow Jobs](https://console.cloud.google.com/dataflow)
