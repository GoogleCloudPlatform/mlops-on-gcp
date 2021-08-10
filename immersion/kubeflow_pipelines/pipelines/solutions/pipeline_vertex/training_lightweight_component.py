"""Pipeline training light-weight component function."""



def train_and_deploy(
        project: str,
        location: str,
        container_uri: str,
        training_file_path: str,
        validation_file_path: str,
        staging_bucket: str,
        job_dir: str,
        alpha: float, 
        max_iter: int,
    ):
    from google.cloud import aiplatform
    
    
    SERVING_CONTAINER_IMAGE_URI = 'us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.0-20:latest'

    aiplatform.init(project=project, location=location,
                    staging_bucket=staging_bucket)
    job = aiplatform.CustomContainerTrainingJob(
        display_name='covertype_kfp_training',
        container_uri=container_uri,
        command=[
            "python", 
            "train.py",
            f"--job_dir={job_dir}",
            f"--training_dataset_path={training_file_path}",
            f"--validation_dataset_path={validation_file_path}",
            f"--alpha={alpha}",
            f"--max_iter={max_iter}",
            "--nohptune"
        ],
        staging_bucket=staging_bucket,
        model_serving_container_image_uri=SERVING_CONTAINER_IMAGE_URI,
    )
    model = job.run(replica_count=1, model_display_name='covertype_kfp_model')
    endpoint = model.deploy(
        traffic_split={"0": 100},
        machine_type='n1-standard-2',
    )