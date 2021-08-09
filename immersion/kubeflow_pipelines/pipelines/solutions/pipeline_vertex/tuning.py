"""Pipeline tuning light-weight component function."""
from typing import NamedTuple


def tune_hyperparameters(
        project: str,
        location: str,
        container_uri: str,
        training_file_path: str,
        validation_file_path: str,
        staging_bucket: str,
        job_dir: str,
        max_trial_count: int,
        parallel_trial_count: int
        
) -> NamedTuple('Outputs', [
    ("best_acuracy", float),
    ("best_alpha", float),
    ("best_max_iter", int)
]):
    from google.cloud import aiplatform
    from google.cloud.aiplatform import hyperparameter_tuning as hpt

    aiplatform.init(project=project, location=location, staging_bucket=staging_bucket)
    
    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": "n1-standard-4",
                "accelerator_type": "NVIDIA_TESLA_K80",
                "accelerator_count": 1,
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": container_uri,
                "args": [
                    f"--job_dir={job_dir}",
                    f"--training_dataset_path={training_file_path}",
                    f"--validation_dataset_path={validation_file_path}",
                    "--hptune"                    
                ],
            },
        }
    ]
    
    custom_job = aiplatform.CustomJob(
        display_name='covertype_kfp_trial_job',
        worker_pool_specs=worker_pool_specs
    )
    
    hp_job = aiplatform.HyperparameterTuningJob(
        display_name='covertype_kfp_tuning_job',
        custom_job=custom_job,
        metric_spec={
            'accuracy': 'maximize',
        },
        parameter_spec={
            'alpha': hpt.DoubleParameterSpec(min=1.0e-4, max=1.0e-1, scale='linear'),
            'max_iter': hpt.DiscreteParameterSpec(values=[1, 2], scale='linear')
        },
        max_trial_count=max_trial_count,
        parallel_trial_count=parallel_trial_count,
    )

    hp_job.run()
    
    metrics = [trial.final_measurement.metrics[0].value for trial in hp_job.trials]
    best_trial = hp_job.trials[metrics.index(max(metrics))]
    best_accuracy = float(best_trial.final_measurement.metrics[0].value)
    best_alpha = float(best_trial.parameters[0].value)
    best_max_iter = int(best_trial.parameters[1].value)
    
    return best_accuracy, best_alpha, best_max_iter