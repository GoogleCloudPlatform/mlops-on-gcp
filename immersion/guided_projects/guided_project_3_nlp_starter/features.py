"""Covertype model features."""
import tensorflow as tf
import tensorflow_model_analysis as tfma
import tensorflow_transform as tft
from tensorflow_transform.tf_metadata import schema_utils


NUMERIC_FEATURE_KEYS = []

CATEGORICAL_FEATURE_KEYS = ['title']

LABEL_KEY = 'source'

def transformed_name(key):
    return key + '_xf'


