FROM tensorflow/tensorflow:2.4.0rc0
RUN pip install tensorflow_datasets

ADD mnist mnist

ENTRYPOINT ["python", "-m", "mnist.main"]
