FROM python:3.8.2-slim

RUN pip install PyMySQL google-cloud-storage && \
    pip install mlflow[extras]==1.8.0

ENTRYPOINT ["mlflow", "server"]
