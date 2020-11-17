#!/usr/bin/env python3

import json
import logging
import math
import os

import boto3
import fiona

AWS_BATCH_ARRAY_SIZE_LIMIT = 10000
MIN_FEATURES_PER_JOB = 100

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def push_training_collection(bucket, project_id):
    """
    Push a training data collection job to Batch.
    """
    # Compute number of geometries to process.
    s3 = boto3.client('s3')
    config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
    config = json.loads(config['Body'].read())
    geo_object = s3.get_object(
        Bucket=bucket,
        Key=project_id + '/{}'.format(config['training_geofile'])
    )
    feature_count = 0
    with fiona.open(geo_object['Body']) as src:
        for feat in src:
            feature_count += 1
    logging.info('Found {} features.'.format(feature_count))

    # Determine batch array size.
    limit_factor = math.ceil(feature_count / AWS_BATCH_ARRAY_SIZE_LIMIT)
    features_per_job = limit_factor * MIN_FEATURES_PER_JOB
    batch_array_size = math.ceil(feature_count / features_per_job)

    # Setup the job dict.
    job = {
        'jobQueue': 'fetch-and-run-queue',
        'jobDefinition': 'first-run-job-definition',
        'jobName': 'collect-{}'.format(project_id),
        'arrayProperties': {'size': batch_array_size},
        'containerOverrides': {
            'environment': [
                {'name': 'AWS_ACCESS_KEY_ID', 'value': os.environ.get('AWS_ACCESS_KEY_ID')},
                {'name': 'AWS_SECRET_ACCESS_KEY', 'value': os.environ.get('AWS_SECRET_ACCESS_KEY')},
                {'name': 'PIXELS_PROJECT_ID', 'value': project_id},
                {'name': 'AWS_S3_BUCKET', 'value': bucket},
                {'name': 'BATCH_FILE_S3_URL', 'value': 's3://tesselo-pixels-scripts/batch.zip'},
                {'name': 'BATCH_FILE_TYPE', 'value': 'zip'},
                {'name': 'BATCH_FEATURES_PER_JOB', 'value': str(features_per_job)}
            ],
            'vcpus': 2,
            'memory': 1024 * 2,
            'command': ['collect.py']
        },
        'retryStrategy': {
            'attempts': 1
        },
    }
    logging.info(job)

    # Push training collection job.
    batch = boto3.client('batch', region_name='eu-central-1')
    return batch.submit_job(**job)


# Get path from env.
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
project = os.environ.get('PIXELS_PROJECT_ID')
if project is None:
    raise ValueError('Specify PIXELS_PROJECT_ID env var.')
jobid = push_training_collection(bucket, project)
print(jobid)
