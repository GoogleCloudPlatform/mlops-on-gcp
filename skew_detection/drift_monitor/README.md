# Data Drift Monitoring

This folder contains a Dataflow Flex template and helper utilities to run and schedule Dataflow jobs that analyze AI Platform Prediction request-response log with a goal of identifying data drift and skew.

- `log_analyzer` - Log Analyzer Dataflow Flex template
- `job_scheduler` - Log Analyzer CLI to help with running and scheduling the template runs.
- `sample_file` - schema, baseline statistics, and simulated request-response log that can be used for a quick test of the log analyzer and scheduler

Follow the README files in the component folders for more information.

