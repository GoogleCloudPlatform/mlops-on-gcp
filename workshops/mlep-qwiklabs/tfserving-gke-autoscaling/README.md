## Lab Overview

TBD

TF Serving is deployed as a Kubernetes Deployment and exposed as a Kubernetes Service. 
The number of replicas in the deployment is controlled by Horizontal Pod Autoscaler based on 
the CPU utilization metrics.


## Setup and Requirements

Set the default compute zone

```
PROJECT_ID=jk-mlops-dev
gcloud config set project $PROJECT_ID
gcloud config set compute/zone us-central1-f
```

## Creating a Kubernetes cluster

To create a new cluster with 3 nodes in the default node pool, run the following command.


```
CLUSTER_NAME=lab1-cluster

gcloud beta container clusters create $CLUSTER_NAME \
  --cluster-version=latest \
  --machine-type=n1-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=3 \
  --num-nodes=1 
```

Check that the cluster is up and running

```
gcloud container clusters list
```

Get the credentials for you new cluster so you can interact with it using `kubectl`.

```
gcloud container clusters get-credentials $CLUSTER_NAME 
```

List the cluster's nodes.

```
kubectl get nodes
```

Notice that the cluster has only one node.




## Deploying a model.


Update and create the ConfigMap with the resnet_serving model location.

```
kubectl apply -f tf-serving/configmap.yaml
```

Create TF Serving Deployment.

```
kubectl apply -f tf-serving/deployment.yaml
```


Create  TF Serving Service.

```
kubectl apply -f tf-serving/service.yaml
```

Get the external address for the TF Serving service

```
kubectl get svc image-classifier
```

Verify that the model is up and operational.

```
curl -d @locust/request-body.json -X POST http://[EXTERNAL_IP]:8501/v1/models/image_classifier:predict
```

Configure Horizontal Pod Autoscaler.

```
kubectl autoscale deployment image-classifier --cpu-percent=60 --min=1 --max=4
```

Check the status of the autoscaler.

```
kubectl get hpa
```



## Load test the model

```
cd locust
locust -f tasks.py --headless --users 32 --spawn-rate 1 --step-load --step-users 1 --step-time 30s --host http://[EXTERNAL_IP]:8501
```

Observe the TF Serving Deployment in GKE dashboard.

```
https://console.cloud.google.com/kubernetes/deployment/us-central1-f/lab1-cluster/default/image-classifier/overview
```

Observe the default node-pool

```
https://console.cloud.google.com/kubernetes/nodepool/us-central1-f/lab1-cluster/default-pool
```