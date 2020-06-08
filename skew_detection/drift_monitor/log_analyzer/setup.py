from setuptools import find_packages
from setuptools import setup


setup(
    name='log_analyzer',
    description='CAIP request-response log analyzer.',
    version='0.1',
    packages=find_packages(),
    install_requires=[
      'tensorflow-data-validation[visualization]==0.22.0',
      'jinja2'
    ]
)