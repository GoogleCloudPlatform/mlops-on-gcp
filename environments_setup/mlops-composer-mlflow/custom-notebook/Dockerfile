FROM gcr.io/deeplearning-platform-release/base-cpu:latest
RUN apt update && apt -y install mysql-client kubectl
COPY entrypoint.sh .
COPY requirements.txt .
RUN python -m pip install -U -r requirements.txt --ignore-installed PyYAML==5.3.1
RUN curl -o /usr/local/bin/cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 && \
    chmod +x /usr/local/bin/cloud_sql_proxy && \
    chmod +x /entrypoint.sh
