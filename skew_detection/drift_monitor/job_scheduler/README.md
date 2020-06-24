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

You can use [Google Cloud Console](https://console.cloud.google.com/cloudtasks) or the `gcloud tasks queues create` command to create a queue for dispatching Log Analyzer jobs. Use the default queues settings for the intial configuration. If you want to fine tune how the jobs are dispatched follow the guidelines in the [Cloud Tasks Documentation](https://cloud.google.com/tasks/docs/configuring-queues).

To create the queue using the `gcloud tasks queues create` command:

```
gcloud tasks queues create [YOUR_QUEUE_NAME]
```


### Creating a Cloud Tasks service account

You also need to set up a service account that will be used to call the Dataflow Flex Template service. This account needs to have permissions to enqueue tasks and to access the service. You will refer to this account when scheduling the Log Analyzer jobs.

```
SERVICE_ACCOUNT_NAME=[YOUR_SA_NAME]
PROJECT_ID=[YOUR_PROJECT_ID]
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --description="[SA_DESCRIPTION]" \
    --display-name="[SA_DISPLAY_NAME]"
    
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role roles/cloudtasks.enqueuer 
  
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role roles/iam.serviceAccountUser 
  
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role roles/iam.serviceAccountTokenCreator
  
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role roles/dataflow.developer
  
```

### Scheduling a Log Analyzer job

After configuring the queue and the service account, you can use the `dms schedule` command to schedule the Log Analyzer jobs.

Use `dms schedule --help` for the detailed list of runtime parameters.
