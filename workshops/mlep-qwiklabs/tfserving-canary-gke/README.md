# Canary releases of ML models using GKE and Istio

## Introduction

Istio is an open source framework for connecting, securing, and managing microservices, including services running on Google Kubernetes Engine (GKE). It lets you create a network of deployed services with load balancing, service-to-service authentication, monitoring, and more, without requiring any changes in service code.

This lab shows you how to use Istio on Kubernetes Engine to facilitate progressive delivery of TensorFlow machine learning model served through TF Serving.




## Setup and Requirements

### Qwiklabs setup

### Activate Cloud Shell

## Setting up your GKE cluster


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

### Configuring automatic sidecar injection

```
kubectl label namespace default istio-injection=enabled
```

## Deploying ResNet50.

In our scenario ResNet50 is a current production model.

Update and create the ConfigMap with the location of the ResNet50 SavedModel.

```
kubectl apply -f tf-serving/configmap-resnet50.yaml
```

Deploy ResNet50 model using TF Serving.

```
kubectl apply -f tf-serving/deployment-resnet50.yaml
```

Show containers in the pod 

```
TBD
```

Notice that the pod contains two containers: `tf-serving` and `istio-proxy`

Create the service that provides access to the deployment.

```
kubectl apply -f tf-serving/service.yaml
```




### Configure access to the model through Istio Ingress gateway


Create Istio Gateway that accepts calls from any hosts.

```
kubectl apply -f tf-serving/gateway.yaml
```


Create a virtual service that routes the traffic to all deployments labeled `image-classifier`. At this point this will only be the ResNet50 deployment.


```
kubectl apply -f tf-serving/virtualservice.yaml
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

Note that the model ranked the `military uniform` label with the highest probability of around 45%.

## Deploying ResNet101 model as a Canary release

### Prepare Istio for Canary routing
Let's now deploy **ResNet101** model as a canary release of the image classifier service.

Start by creating  destination rule that defines named service subsets for the image-classifier service.
One subset will reference the ResNet50 deployment the other the ResNet101 deployment.

```
kubectl apply -f tf-serving/destinationrule.yaml
```

Reconfigure the virtual service to route 100% traffic to the ResNet50 subset and 0% traffic to the ResNet100 subset.

```
kubectl apply -f tf-serving/virtualservice-weight-100.yaml
```


Invoke the service. 

```
curl -d @locust/request-body.json -X POST http://$GATEWAY_URL/v1/models/image_classifier:predict
```

Repeat a few times. Note that the requests continue to be routed to the ResNet50 model.

### Deploy ResNet101


Update and create the ConfigMap with the location of the ResNet101 SavedModel.

```
kubectl apply -f tf-serving/configmap-resnet101.yaml
```

Deploy ResNet50 model using TF Serving.

```
kubectl apply -f tf-serving/deployment-resnet101.yaml
```
 
Wait for the deployment to come live.

```
kubectl get deployments -o wide
```

The ResNet101 deployment is ready but the virtual service is still routing all requests to ResNet50.

Verify but sending a few requests to the service.

```
curl -d @locust/request-body.json -X POST http://$GATEWAY_URL/v1/models/image_classifier:predict
```

We are still getting the same response.

### Reconfigure Istio to split traffic between ResNet50 and ResNet101

Modify the virtual service to route 70% requests to ResNet50 and 30% to ResNet101

```
kubectl apply -f tf-serving/virtualservice-weight-70.yaml
```

Send a few more requests - more than 10

```
curl -d @locust/request-body.json -X POST http://$GATEWAY_URL/v1/models/image_classifier:predict
```

Notice that some responses are now different. The probability assigned to the `military uniform` label is around 94%.
These are the responses from the Canary ResNet101 release.


As an optional task please reconfigure the virtual service to route 100% traffic to the ResNet101 model.

### Configuring focused canary testing.

In the previous steps you learned how to control fine-grained traffic percentages. 
Istio routing rules allow for much more sophisticated canary testing scenarios.

In this section, you will reconfigure the `image-classifier` virtual service to route traffic to the canary deployment based on request host headers.
This approach allows a variety scenarios, including allocate a subset of users to canary testing.
Let's assume that the request from the canary users will carry a custom header `user-group`. If this header is set to `canary` the request will be routed to ResNet101.

```
kubectl apply -f tf-serving/virtualservice-focused-routing.yaml
```

Send a few requests without the `user-group` header.

```
curl -d @locust/request-body.json -X POST http://$GATEWAY_URL/v1/models/image_classifier:predict
```

Now send a few requests with the `user-group` header set to `canary`.


```
curl -d @locust/request-body.json -H "user-group: canary" -X POST http://$GATEWAY_URL/v1/models/image_classifier:predict
```


