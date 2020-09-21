import shutil
import numpy as np
import tensorflow as tf

tf.logging.set_verbosity(tf.logging.INFO)

BUCKET = None  # set from task.py
PATTERN = 'of' # gets all files

# Determine CSV, label, and key columns
CSV_COLUMNS = 'weight_pounds,is_male,mother_age,plurality,gestation_weeks,key'.split(',')
LABEL_COLUMN = 'weight_pounds'
KEY_COLUMN = 'key'

# Set default values for each CSV column
DEFAULTS = [[0.0], ['null'], [0.0], ['null'], [0.0], ['nokey']]

# Define some hyperparameters
TRAIN_STEPS = 10000
EVAL_STEPS = None
BATCH_SIZE = 512
NEMBEDS = 3
NNSIZE = [64, 16, 4]

# Create an input function reading a file using the Dataset API
# Then provide the results to the Estimator API
def read_dataset(prefix, mode, batch_size):
    def _input_fn():
        def decode_csv(value_column):
            columns = tf.decode_csv(value_column, record_defaults=DEFAULTS)
            features = dict(zip(CSV_COLUMNS, columns))
            label = features.pop(LABEL_COLUMN)
            return features, label
        
        # Use prefix to create file path
        file_path = 'gs://{}/babyweight/preproc/{}*{}*'.format(BUCKET, prefix, PATTERN)

        # Create list of files that match pattern
        file_list = tf.gfile.Glob(file_path)

        # Create dataset from file list
        dataset = (tf.data.TextLineDataset(file_list)  # Read text file
                    .map(decode_csv))  # Transform each elem by applying decode_csv fn
      
        if mode == tf.estimator.ModeKeys.TRAIN:
            num_epochs = None # indefinitely
            dataset = dataset.shuffle(buffer_size = 10 * batch_size)
        else:
            num_epochs = 1 # end-of-input after this
 
        dataset = dataset.repeat(num_epochs).batch(batch_size)
        return dataset.make_one_shot_iterator().get_next()
    return _input_fn

# Define feature columns
def get_wide_deep():
    # Define column types
    is_male,mother_age,plurality,gestation_weeks = \
        [\
            tf.feature_column.categorical_column_with_vocabulary_list('is_male', 
                        ['True', 'False', 'Unknown']),
            tf.feature_column.numeric_column('mother_age'),
            tf.feature_column.categorical_column_with_vocabulary_list('plurality',
                        ['Single(1)', 'Twins(2)', 'Triplets(3)',
                         'Quadruplets(4)', 'Quintuplets(5)','Multiple(2+)']),
            tf.feature_column.numeric_column('gestation_weeks')
        ]

    # Discretize
    age_buckets = tf.feature_column.bucketized_column(mother_age, 
                        boundaries=np.arange(15,45,1).tolist())
    gestation_buckets = tf.feature_column.bucketized_column(gestation_weeks, 
                        boundaries=np.arange(17,47,1).tolist())
      
    # Sparse columns are wide, have a linear relationship with the output
    wide = [is_male,
            plurality,
            age_buckets,
            gestation_buckets]
    
    # Feature cross all the wide columns and embed into a lower dimension
    crossed = tf.feature_column.crossed_column(wide, hash_bucket_size=20000)
    embed = tf.feature_column.embedding_column(crossed, NEMBEDS)
    
    # Continuous columns are deep, have a complex relationship with the output
    deep = [mother_age,
            gestation_weeks,
            embed]
    return wide, deep

# Create serving input function to be able to serve predictions later using provided inputs
def serving_input_fn():
    feature_placeholders = {
        'is_male': tf.placeholder(tf.string, [None]),
        'mother_age': tf.placeholder(tf.float32, [None]),
        'plurality': tf.placeholder(tf.string, [None]),
        'gestation_weeks': tf.placeholder(tf.float32, [None]),
        KEY_COLUMN: tf.placeholder_with_default(tf.constant(['nokey']), [None])
    }
    features = {
        key: tf.expand_dims(tensor, -1)
        for key, tensor in feature_placeholders.items()
    }
    return tf.estimator.export.ServingInputReceiver(features, feature_placeholders)

# create metric for hyperparameter tuning
def my_rmse(labels, predictions):
    pred_values = predictions['predictions']
    return {'rmse': tf.metrics.root_mean_squared_error(labels, pred_values)}

# Create estimator to train and evaluate
def train_and_evaluate(output_dir):
    tf.summary.FileWriterCache.clear() # ensure filewriter cache is clear for TensorBoard events file
    wide, deep = get_wide_deep()
    EVAL_INTERVAL = 300 # seconds

    ## TODO 2a: set the save_checkpoints_secs to the EVAL_INTERVAL
    run_config = tf.estimator.RunConfig(save_checkpoints_secs = EVAL_INTERVAL,
                                        keep_checkpoint_max = 3)
    
    ## TODO 2b: change the dnn_hidden_units to NNSIZE
    estimator = tf.estimator.DNNLinearCombinedRegressor(
        model_dir = output_dir,
        linear_feature_columns = wide,
        dnn_feature_columns = deep,
        dnn_hidden_units = NNSIZE,
        config = run_config)
    
    # illustrates how to add an extra metric
    estimator = tf.contrib.estimator.add_metrics(estimator, my_rmse)
    # for batch prediction, you need a key associated with each instance
    estimator = tf.contrib.estimator.forward_features(estimator, KEY_COLUMN)
    
    ## TODO 2c: Set the third argument of read_dataset to BATCH_SIZE 
    ## TODO 2d: and set max_steps to TRAIN_STEPS
    train_spec = tf.estimator.TrainSpec(
        input_fn = read_dataset('train', tf.estimator.ModeKeys.TRAIN, BATCH_SIZE),
        max_steps = TRAIN_STEPS)
    
    exporter = tf.estimator.LatestExporter('exporter', serving_input_fn, exports_to_keep=None)

    ## TODO 2e: Lastly, set steps equal to EVAL_STEPS
    eval_spec = tf.estimator.EvalSpec(
        input_fn = read_dataset('eval', tf.estimator.ModeKeys.EVAL, 2**15),  # no need to batch in eval
        steps = EVAL_STEPS,
        start_delay_secs = 60, # start evaluating after N seconds
        throttle_secs = EVAL_INTERVAL,  # evaluate every N seconds
        exporters = exporter)
    tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)
