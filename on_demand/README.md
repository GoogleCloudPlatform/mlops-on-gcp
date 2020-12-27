# On-Demand

This directory contains labs for the MLOps on Google Cloud on Coursera specialization. 

These labs are separated from workshop labs to:

*  Enable customization of labs for on-demand delivery
*  Provide greater reliability and maintainability through pinning labs to stable KFP and TFX versions


## Learner lab setup instructions

1.  Create AI Platform Notebooks instance and open a Jupyterlab terminal.
2.  Install ktp, a container toolkit, for downloading just the on-demand lab directory.

```
sudo apt-get install google-cloud-sdk-kpt
```

3.  Install the on-demand lab directory by running the following command from the terminal:

```
SRC_REPO=https://github.com/GoogleCloudPlatform/mlops-on-gcp
kpt pkg get $SRC_REPO/on_demand on_demand
```
