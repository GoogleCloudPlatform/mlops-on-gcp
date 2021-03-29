# Canary releases of ML models using GKE and Istio

## Introduction

Istio is an open source framework for connecting, securing, and managing microservices, including services running on Google Kubernetes Engine (GKE). It lets you create a network of deployed services with load balancing, service-to-service authentication, monitoring, and more, without requiring any changes in service code.

This lab shows you how to use Istio on Kubernetes Engine to facilitate progressive delivery of TensorFlow machine learning model served through TF Serving.




## Setup and Requirements

### Qwiklabs setup

### Activate Cloud Shell

## Set up your GKE cluster


Set the project ID

```
PROJECT_ID=jk-mlops-dev
gcloud config set project $PROJECT_ID
gcloud config set compute/zone us-central1-f
```

### Creating a Kubernetes cluster with Istio

Set the name and the zone for your cluster

```
CLUSTER_NAME=lab2-cluster
```

Create a GKE cluster with Istio enabled and with mTLS in permissive mode:

```
gcloud beta container clusters create $CLUSTER_NAME \
  --project=$PROJECT_ID \
  --addons=Istio \
  --istio-config=auth=MTLS_PERMISSIVE \
  --cluster-version=latest \
  --machine-type=n1-standard-8 \
  --num-nodes=3 

```

### Verifying the installation

Check that the cluster is up and running

```
gcloud container clusters list
```

Get the credentials for you new cluster so you can interact with it using `kubectl`.

```
gcloud container clusters get-credentials $CLUSTER_NAME
```

Ensure the following Kubernetes services are deployed: `istio-citadel`, `istio-egressgateway`, `istio-pilot`, `istio-ingressgateway`, `istio-policy`, `istio-sidecar-injector`, and `istio-telemetry`

```
kubectl get service -n istio-system
```

Ensure that the corresponding Kubernetes Pods are deployed and all containers are up and running: `istio-pilot-*`, `istio-policy-*`, `istio-telemetry-*`, `istio-egressgateway-*`, `istio-ingressgateway-*`, `istio-sidecar-injector-*`, and `istio-citadel-*`

```
kubectl get pods -n istio-system
```

## Deploying ResNet50 and ResNet101 models.

Update and create the ConfigMap with the location of ResNet50 and ResNet101 SavedModels

```
kubectl apply -f tf-serving/configmap.yaml
```

Create deployments for ResNet101 and ResNet50 models.

```
kubectl apply -f tf-serving/deployments.yaml
```

Verify that the deployments are operational. You may need to wait a little bit before the pods are in the READY state. Note that each deployment has one pod and that the pod contains one container - `tf-serving`.

```
kubectl get deployments -o wide
```

Create the service that exposes an external load balancer to the model deployments.

```
kubectl apply -f tf-serving/service-loadbalancer.yaml
```

Navigate to `https://console.cloud.google.com/kubernetes/service/us-central1-f/lab2-cluster/default/image-classifier/overview` to verify that the service load balances between pods from both deployments by checking the **Serving pods** section of the page. You should see two pods with the names starting with `image-classifier-resnet101` and `image-classifier-resnet50`.


Get the external address for the image classifier service. It may take a couple of minutes before the external IP has been provisioned.

```
kubectl get svc image-classifier
```

Submit the request to the service.


```
curl -d @locust/request-body.json -X POST http://[EXTERNAL_IP]:8501/v1/models/image_classifier:predict
```


Repeat a few times. Notice that the responses differ between calls. This is due to load balancing between different models.

## Configuring Istio

### Inject Istio side cars 

```
istioctl kube-inject -f tf-serving/deployments.yaml | kubectl apply -f -
```

Verify that pods in both deployments contain two containers: `tf-serving` and `istio-proxy`.

```
kubectl get deployments -o wide
```


### Configure Istio Gateway and destination rules.

We will be accessing the deployments through Istio Gateway.

Change the `image-classifier` service type from **LoadBalancer** to **ClusterIP**.


```
kubectl delete -f tf-serving/service-loadbalancer.yaml
kubectl apply -f tf-serving/service.yaml
```

Verify that the `image-classifier` service is operational

```
kubectl get svc image-classifier -o wide
```

Create Istio Gateway that accepts calls from any hosts.

```
kubectl apply -f tf-serving/gateway.yaml
```

Create a destination rule that defines named service subsets for the `image-classifier` service.

```
kubectl apply -f tf-serving/destinationrule.yaml
```


### Route 100% traffic to ResNet50

Create a virtual service that distributes 100% of traffic to ResNet50 


```
kubectl apply -f tf-serving/virtualservice-weight-routing.yaml
```

### Test the service

Check the configuration of the Istio Ingress Gateway

```
kubectl get svc istio-ingressgateway -n istio-system
```

Set the Ingress IP and ports

```
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
```

Set the gateway URL
```
export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT
```

Send a request to the service.

```
curl -d @locust/request-body.json -X POST http://$GATEWAY_URL/v1/models/image_classifier:predict
```

Repeat a few times. Notice that more responses come from ResNet50. 

