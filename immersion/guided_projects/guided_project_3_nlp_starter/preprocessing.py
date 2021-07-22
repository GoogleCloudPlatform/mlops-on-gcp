
import tensorflow as tf
import tensorflow_model_analysis as tfma
import tensorflow_transform as tft
from tensorflow_transform.tf_metadata import schema_utils


FEATURE_KEY = 'title'
LABEL_KEY = 'source'
N_CLASSES = 3


def _fill_in_missing(x):
    default_value = '' if x.dtype == tf.string else 0
    return tf.squeeze(
        tf.sparse.to_dense(
            tf.SparseTensor(x.indices, x.values, [x.dense_shape[0], 1]),
            default_value),
        axis=1)


def transformed_name(key):
    return key + '_xf'


def process_labels(raw_labels):
    integerized_labels = tft.compute_and_apply_vocabulary(
        raw_labels, num_oov_buckets=0, vocab_filename=LABEL_KEY)
    one_hot_labels = tf.one_hot(integerized_labels, depth=N_CLASSES)
    return one_hot_labels


def preprocessing_fn(inputs):
    features = _fill_in_missing(inputs[FEATURE_KEY])
    raw_labels =  _fill_in_missing(inputs[LABEL_KEY])
    labels = process_labels(raw_labels)
    
    return {
        transformed_name(FEATURE_KEY): features,
        transformed_name(LABEL_KEY): labels
    }
