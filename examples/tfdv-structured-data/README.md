# Analyzing and validating data with TensorFlow Data Validation.

In this lab, you will learn how to use TensorFlow Data Validation (TFDV) for structured data analysis and validation:
- Generating descriptive statistics, 
- Inferring and fine tuning schema, 
- Checking for and fixing data anomalies,
- Detecting drift and skew. 


## Lab Setup
### AI Platform Notebook configuration
You will use the **AI Platform Notebooks** instance configured with a custom container image. This lab requires a specific image that is different than one used by other labs and provisioned in `lab-01-environment-notebook`.


To prepare the **AI Platform Notebooks** instance:

1. Start GCP Cloud Shell
2. Create a working folder in your `home` directory
```
cd
mkdir lab-31-workspace
cd lab-31-workspace
```
2. Create Dockerfile
```
cat > Dockerfile << EOF
FROM gcr.io/deeplearning-platform-release/tf-cpu.1-15
RUN pip install -U six==1.12 apache-beam==2.16 pyarrow==0.14.0 tfx-bsl==0.15.1 \
&& pip install -U tfx==0.15 
EOF
```
3. Build and push the image to your project's Container Registry
```
PROJECT_ID=$(gcloud config get-value core/project)
IMAGE_NAME=tfx-dev
TAG=TF115-TFX015

IMAGE_URI="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${TAG}"

gcloud builds submit --timeout 15m --tag ${IMAGE_URI} .
```
4. Provision the **AI Platform Notebook** instance based on a custom container image, following the  [instructions in AI Platform Notebooks Documentation](https://cloud.google.com/ai-platform/notebooks/docs/custom-container). In the **Docker container image** field, enter the following image name: `gcr.io/[YOUR_PROJECT_ID]/tfx-dev:TF115-TFX015`.
5. Connect to **JupyterLab** and clone this repo under the `/home` directory

### Lab dataset
This lab uses the [Covertype Dat Set](../datasets/covertype/README.md). 

### GCS staging bucket

Create the GCS bucket that will be used as a staging area during the lab.
```
PROJECT_ID=[YOUR_PROJECT_ID]
BUCKET_NAME=gs://${PROJECT_ID}-staging
gsutil mb -p $PROJECT_ID $BUCKET_NAME
```

## Lab Exercises
This lab has two exercises:
1. The [tfdv-covertype.ipynb](tfdv-covertype.ipynb) Notebook, which uses the [Covertype Dataset](../datasets/covertype/README.md) available in the repository. This exersise is intended to run locally.
2. The [tfdv-flights.ipynb](tfdv-flights.ipynb) Notebook, which uses the [flights](https://bigquery.cloud.google.com/table/bigquery-samples:airline_ontime_data.flights?pli=1&tab=schema) dataset available in BigQuery. This exersise is intended to run the TFDV steps using Dataflow.

