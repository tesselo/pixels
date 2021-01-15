#!/usr/bin/env python3

import json
import logging
import math
import os

import boto3
import fiona

AWS_BATCH_ARRAY_SIZE_LIMIT = 10000

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def push_training_collection(command, bucket, project_id, features_per_job=50):
    """
    Push a training data collection job to Batch.
    """
    if command not in ["collect", "predict"]:
        raise ValueError("Unknown command {}.".format(command))
    # Compute number of geometries to process.
    s3 = boto3.client("s3")
    config = s3.get_object(Bucket=bucket, Key=project_id + "/config.json")
    config = json.loads(config["Body"].read())
    geo_object = s3.get_object(
        Bucket=bucket, Key=project_id + "/{}".format(config["training_geofile"])
    )
    with fiona.open(geo_object["Body"]) as src:
        feature_count = len(src)
    logging.info("Found {} features.".format(feature_count))

    # Determine batch array size.
    batch_array_size = math.ceil(feature_count / features_per_job)
    if batch_array_size > AWS_BATCH_ARRAY_SIZE_LIMIT:
        raise ValueError(
            "Array size {} above limit of {}, please increase features per job.".format(
                batch_array_size, AWS_BATCH_ARRAY_SIZE_LIMIT
            )
        )

    # Setup the job dict.
    job = {
        "jobQueue": "fetch-and-run-queue",
        "jobDefinition": "first-run-job-definition",
        "jobName": "{}-{}".format(command, project_id),
        "arrayProperties": {"size": batch_array_size},
        "containerOverrides": {
            "environment": [
                {
                    "name": "AWS_ACCESS_KEY_ID",
                    "value": os.environ.get("AWS_ACCESS_KEY_ID"),
                },
                {
                    "name": "AWS_SECRET_ACCESS_KEY",
                    "value": os.environ.get("AWS_SECRET_ACCESS_KEY"),
                },
                {"name": "PIXELS_PROJECT_ID", "value": project_id},
                {"name": "AWS_S3_BUCKET", "value": bucket},
                {
                    "name": "BATCH_FILE_S3_URL",
                    "value": "s3://tesselo-pixels-scripts/batch.zip",
                },
                {"name": "BATCH_FILE_TYPE", "value": "zip"},
                {"name": "BATCH_FEATURES_PER_JOB", "value": str(features_per_job)},
                {"name": "DB_NAME", "value": os.environ.get("DB_NAME")},
                {"name": "DB_PASSWORD", "value": os.environ.get("DB_PASSWORD")},
                {"name": "DB_HOST", "value": os.environ.get("DB_HOST")},
                {"name": "DB_USER", "value": os.environ.get("DB_USER")},
            ],
        },
        "retryStrategy": {"attempts": 1},
    }
    # Choose collect or predict mode.
    if command == "collect":
        job["containerOverrides"].update(
            {
                "vcpus": 2,
                "memory": 1024 * 2,
                "command": ["collect.py"],
            }
        )
    else:
        job["containerOverrides"].update(
            {
                "vcpus": 8,
                "memory": int(1024 * 30.5),
                "resourceRequirements": [
                    {
                        "type": "GPU",
                        "value": "1",
                    }
                ],
                "command": ["predict.py"],
            }
        )
    logging.info(job)
    # Push training collection job.
    batch = boto3.client("batch", region_name="eu-central-1")
    return batch.submit_job(**job)


# Get data from env.
command = os.environ.get("PIXELS_COMMAND")
bucket = os.environ.get("AWS_S3_BUCKET", "tesselo-pixels-results")
project = os.environ.get("PIXELS_PROJECT_ID")
features_per_job = int(os.environ.get("BATCH_FEATURES_PER_JOB", 50))
if project is None:
    raise ValueError("Specify PIXELS_PROJECT_ID env var.")
jobid = push_training_collection(command, bucket, project, features_per_job)
print(jobid)
