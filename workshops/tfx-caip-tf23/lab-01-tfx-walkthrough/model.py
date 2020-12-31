# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The Covertype classifier DNN keras model."""

import absl
import os
from typing import List, Text

import tensorflow as tf
import tensorflow_model_analysis as tfma
import tensorflow_transform as tft
from tensorflow_transform.tf_metadata import schema_utils

from tfx.components.trainer.executor import TrainerFnArgs
from tfx.components.trainer.fn_args_utils import DataAccessor
from tfx.components.tuner.component import TunerFnResult
from tfx_bsl.tfxio import dataset_options

import features

HIDDEN_UNITS = [16, 8]
LEARNING_RATE = 0.001
EPOCHS = 3
TRAIN_BATCH_SIZE = 64
EVAL_BATCH_SIZE = 64


def _gzip_reader_fn(filenames):
  """Small utility returning a record reader that can read gzip'ed files."""
  return tf.data.TFRecordDataset(filenames, compression_type='GZIP')


def _get_serve_tf_examples_fn(model, tf_transform_output):
  """Returns a function that parses a serialized tf.Example and applies TFT."""

  model.tft_layer = tf_transform_output.transform_features_layer()

  @tf.function
  def serve_tf_examples_fn(serialized_tf_examples):
    """Returns the output to be used in the serving signature."""
    feature_spec = tf_transform_output.raw_feature_spec()
    parsed_features = tf.io.parse_example(serialized_tf_examples, feature_spec)

    transformed_features = model.tft_layer(parsed_features)
    transformed_features.pop(features.transformed_name(features.LABEL_KEY))

    return model(transformed_features)

  return serve_tf_examples_fn


def _input_fn(file_pattern: List[Text],
              data_accessor: DataAccessor,
              tf_transform_output: tft.TFTransformOutput,
              batch_size: int = 200) -> tf.data.Dataset:
  """Generates features and label for tuning/training.

  Args:
    file_pattern: List of paths or patterns of input tfrecord files.
    data_accessor: DataAccessor for converting input to RecordBatch.
    tf_transform_output: A TFTransformOutput.
    batch_size: representing the number of consecutive elements of returned
      dataset to combine in a single batch

  Returns:
    A dataset that contains (features, indices) tuple where features is a
      dictionary of Tensors, and indices is a single Tensor of label indices.
  """
  dataset = data_accessor.tf_dataset_factory(
      file_pattern,
      dataset_options.TensorFlowDatasetOptions(
          batch_size=batch_size, label_key=features.transformed_name(features.LABEL_KEY)),
      tf_transform_output.transformed_metadata.schema)
    
  return dataset


def _build_keras_model(tf_transform_output, hidden_units, learning_rate):
  """Creates a DNN Keras model for classifying taxi data.
  Args:
    hidden_units: [int], the layer sizes of the DNN (input layer first).
  Returns:
    A keras Model.
  """

  numeric_columns = [
      tf.feature_column.numeric_column(
          key=features.transformed_name(key), 
          shape=())
      for key in features.NUMERIC_FEATURE_KEYS
  ]

  categorical_columns = [
      tf.feature_column.categorical_column_with_identity(
          key=features.transformed_name(key), 
          num_buckets=tf_transform_output.num_buckets_for_transformed_feature(features.transformed_name(key)), 
          default_value=0)
      for key in features.CATEGORICAL_FEATURE_KEYS
  ]

  indicator_columns = [
      tf.feature_column.indicator_column(categorical_column)
      for categorical_column in categorical_columns
  ]

  model = _wide_and_deep_classifier(
      # TODO(b/139668410) replace with premade wide_and_deep keras model
      wide_columns=indicator_columns,
      deep_columns=numeric_columns,
      dnn_hidden_units=hidden_units,
      learning_rate=learning_rate)

  return model


def _wide_and_deep_classifier(wide_columns, deep_columns, dnn_hidden_units, learning_rate):
  """Build a simple keras wide and deep model.
  Args:
    wide_columns: Feature columns wrapped in indicator_column for wide (linear)
      part of the model.
    deep_columns: Feature columns for deep part of the model.
    dnn_hidden_units: [int], the layer sizes of the hidden DNN.
  Returns:
    A Wide and Deep Keras model
  """
  
  input_layers = {
      column.key: tf.keras.layers.Input(name=column.key, shape=(), dtype=tf.float32)
      for column in deep_columns
  }
  
  input_layers.update({
      column.categorical_column.key: tf.keras.layers.Input(name=column.categorical_column.key, shape=(), dtype=tf.int32)
      for column in wide_columns
  })
    
  deep = tf.keras.layers.DenseFeatures(deep_columns)(input_layers)
  for numnodes in dnn_hidden_units:
    deep = tf.keras.layers.Dense(numnodes)(deep)
  wide = tf.keras.layers.DenseFeatures(wide_columns)(input_layers)

  output = tf.keras.layers.Dense(features.NUM_CLASSES, activation='softmax')(
               tf.keras.layers.concatenate([deep, wide]))

  model = tf.keras.Model(input_layers, output)
  model.compile(
      loss='sparse_categorical_crossentropy',
      optimizer=tf.keras.optimizers.Adam(lr=learning_rate),
      metrics=[tf.keras.metrics.SparseCategoricalAccuracy()])
  model.summary(print_fn=absl.logging.info)

  return model


# TFX Trainer will call this function.
def run_fn(fn_args: TrainerFnArgs):
  """Train the model based on given args.
  Args:
    fn_args: Holds args used to train the model as name/value pairs.
  """

  tf_transform_output = tft.TFTransformOutput(fn_args.transform_output)

  train_dataset = _input_fn(
      fn_args.train_files, 
      fn_args.data_accessor, 
      tf_transform_output, 
      TRAIN_BATCH_SIZE)

  eval_dataset = _input_fn(
      fn_args.eval_files, 
      fn_args.data_accessor,
      tf_transform_output, 
      EVAL_BATCH_SIZE)
    
  mirrored_strategy = tf.distribute.MirroredStrategy()
  with mirrored_strategy.scope():
        model = _build_keras_model(
            tf_transform_output=tf_transform_output,
            hidden_units=HIDDEN_UNITS,
            learning_rate=LEARNING_RATE)

  tensorboard_callback = tf.keras.callbacks.TensorBoard(
      log_dir=fn_args.model_run_dir, update_freq='batch')

  model.fit(
      train_dataset,
      epochs=EPOCHS,
      steps_per_epoch=fn_args.train_steps,
      validation_data=eval_dataset,
      validation_steps=fn_args.eval_steps,
      callbacks=[tensorboard_callback])
    
  signatures = {
      'serving_default':
          _get_serve_tf_examples_fn(model,
                                    tf_transform_output).get_concrete_function(
                                        tf.TensorSpec(
                                            shape=[None],
                                            dtype=tf.string,
                                            name='examples')),
  }
  
  model.save(fn_args.serving_model_dir, save_format='tf', signatures=signatures)
    

  
  
