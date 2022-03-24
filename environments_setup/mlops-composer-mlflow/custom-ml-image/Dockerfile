# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the \"License\");
# you may not use this file except in compliance with the License.\n",
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an \"AS IS\" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Start from Deep learning base image. See available options:
# https://cloud.google.com/ai-platform/deep-learning-containers/docs/choosing-container
# CPU only
FROM gcr.io/deeplearning-platform-release/base-cpu:latest

# For GPU accelerated training
# FROM gcr.io/deeplearning-platform-release/base-cu100:latest
# FROM gcr.io/deeplearning-platform-release/base-cu101:latest

COPY sql-access.json /usr/local/bin/
COPY entrypoint.sh .
COPY init.sh .
COPY mlrunner.py /mltrainer/

RUN apt-get update && apt-get install -y --no-install-recommends mysql-client kubectl && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install pandas==1.0.4 click==7.0 PyMySQL==0.9.3 google-cloud-storage==1.28.1 mlflow==1.13.1 apache-airflow==1.10.12 PyYAML==5.3.1 cloudml-hypertune && \
    curl -o /usr/local/bin/cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 && \
    chmod +x /usr/local/bin/cloud_sql_proxy && \
    chmod +x /init.sh && \
    chmod +x /entrypoint.sh

# Turn off base image's ENTYPOINT by redefining a new ENTRYPOINT
ENTRYPOINT ["/entrypoint.sh"]
