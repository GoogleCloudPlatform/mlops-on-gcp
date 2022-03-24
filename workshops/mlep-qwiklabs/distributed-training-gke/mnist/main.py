
# Copyright 2020 Google. All Rights Reserved.
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
# ==============================================================================
"""An example of multi-worker training with Keras model using Strategy API."""

import argparse
import json
import logging
import os

import tensorflow_datasets as tfds
import tensorflow as tf
import mnist.model as mnist

BUFFER_SIZE = 100000


def _scale(image, label):
    """Scales an image tensor."""
    image = tf.cast(image, tf.float32)
    image /= 255
    return image, label


def _is_chief(task_type, task_id):
    """Determines if the replica is the Chief."""
    return task_type is None or task_type == 'chief' or (
        task_type == 'worker' and task_id == 0) 


def _get_saved_model_dir(base_path, task_type, task_id):
    """Returns a location for the SavedModel."""

    saved_model_path = base_path
    if not _is_chief(task_type, task_id):
        temp_dir = os.path.join('/tmp', task_type, str(task_id))
        tf.io.gfile.makedirs(temp_dir)
        saved_model_path = temp_dir

    return saved_model_path


def train(epochs, steps_per_epoch, per_worker_batch, checkpoint_path, saved_model_path):
    """Trains a MNIST classification model using multi-worker mirrored strategy."""

    strategy = tf.distribute.experimental.MultiWorkerMirroredStrategy()
    task_type = strategy.cluster_resolver.task_type
    task_id = strategy.cluster_resolver.task_id
    global_batch_size = per_worker_batch * strategy.num_replicas_in_sync

    with strategy.scope():
        datasets, _ = tfds.load(name='mnist', with_info=True, as_supervised=True)
        dataset = datasets['train'].map(_scale).cache().shuffle(BUFFER_SIZE).batch(global_batch_size).repeat()
        options = tf.data.Options()
        options.experimental_distribute.auto_shard_policy = \
            tf.data.experimental.AutoShardPolicy.DATA
        dataset = dataset.with_options(options)
        multi_worker_model = mnist.build_and_compile_cnn_model()

    callbacks = [
        tf.keras.callbacks.experimental.BackupAndRestore(checkpoint_path)
    ]

    multi_worker_model.fit(dataset, 
                           epochs=epochs, 
                           steps_per_epoch=steps_per_epoch,
                           callbacks=callbacks)

    
    logging.info("Saving the trained model to: {}".format(saved_model_path))
    saved_model_dir = _get_saved_model_dir(saved_model_path, task_type, task_id)
    multi_worker_model.save(saved_model_dir)

if __name__ == '__main__':

  logging.getLogger().setLevel(logging.INFO)
  tfds.disable_progress_bar()

  parser = argparse.ArgumentParser()
  parser.add_argument('--epochs',
                      type=int,
                      required=True,
                      help='Number of epochs to train.')
  parser.add_argument('--steps_per_epoch',
                      type=int,
                      required=True,
                      help='Steps per epoch.')
  parser.add_argument('--per_worker_batch',
                      type=int,
                      required=True,
                      help='Per worker batch.')
  parser.add_argument('--saved_model_path',
                      type=str,
                      required=True,
                      help='Tensorflow export directory.')
  parser.add_argument('--checkpoint_path',
                      type=str,
                      required=True,
                      help='Tensorflow checkpoint directory.')

  args = parser.parse_args()

  train(args.epochs, args.steps_per_epoch, args.per_worker_batch, 
      args.checkpoint_path, args.saved_model_path)
