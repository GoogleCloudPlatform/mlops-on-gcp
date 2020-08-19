## Load testing AI Platform Prediction 

This folder contains configuration manifests and a sample testing script that demonstrate how to provision a testing environment and execute load testing runs using [Locust](locust.io), Google Kubernetes Engine, and Cloud Monitoring.

[manifests](manifests). This folder contains **Kustomize** manifests that deploy a distributed configuration of Locust to a GKE cluster.

[locust_image](locust_image). This folder contains a sample **locustfile** and a Dockerfile for the Locust container image. The locustfile implements load testing of the AI Platform Prediction REST API `predict` method. The Dockerfile is a derivative of the standard Locust image from the Docker Hub and incorporates the locustfile script and its dependencies.

Refer to the `03-perf-testing.ipynb` notebook for more information on how to deploy the test environment and execute load testing runs.

