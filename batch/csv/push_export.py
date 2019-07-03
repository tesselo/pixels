#!/usr/bin/env python3

import logging
import math
import os
import tempfile

import boto3
import geopandas

# General log setup.
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Get logger and set info level for this one.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'pge_placer')
filename = os.environ.get('GEO_FILE_NAME', 'pge_buff200_placer.gpkg')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
tile_group_size = int(os.environ.get('TILE_GROUP_SIZE', 1000))

# Get batch index from env.
array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))

# Fetch geoms.
dir = tempfile.mkdtemp()
s3 = boto3.client('s3')
src = os.path.join(dir, filename)
s3.download_file(Bucket=bucket, Key=project_id + '/' + filename, Filename=src)

# Open
pge_buf200_placer_df = geopandas.read_file(src)

nr_of_geoms = len(pge_buf200_placer_df)

batch_array_size = math.ceil(nr_of_geoms / tile_group_size)

print('Found {} geoms - array size is {} - tile group size is {}'.format(nr_of_geoms, batch_array_size, tile_group_size))

steps = [('2019-03-01', '2019-03-31'), ('2019-04-01', '2019-04-30'), ('2019-05-01', '2019-05-31'), ('2019-06-01', '2019-06-30')]

# Setup the job dict.
all_jobs = []
for start, end in steps:
    print(start, end)
    job = {
        'jobQueue': 'fetch-and-run-queue',
        'jobDefinition': 'first-run-job-definition',
        'containerOverrides': {
            'environment': [
                {'name': 'AWS_ACCESS_KEY_ID', 'value': os.environ.get('AWS_ACCESS_KEY_ID')},
                {'name': 'AWS_SECRET_ACCESS_KEY', 'value': os.environ.get('AWS_SECRET_ACCESS_KEY')},
                {'name': 'ESA_SCIHUB_USERNAME', 'value': os.environ.get('ESA_SCIHUB_USERNAME')},
                {'name': 'ESA_SCIHUB_PASSWORD', 'value': os.environ.get('ESA_SCIHUB_PASSWORD')},
                {'name': 'PROJECT_ID', 'value': project_id},
                {'name': 'GEO_FILE_NAME', 'value': filename},
                {'name': 'TILE_GROUP_SIZE', 'value': str(tile_group_size)},
                {'name': 'START_DATE', 'value': start},
                {'name': 'END_DATE', 'value': end},
                {'name': 'AWS_S3_BUCKET', 'value': bucket},
                {'name': 'BATCH_FILE_S3_URL', 'value': 's3://tesselo-pixels-scripts/batch.zip'},
                {'name': 'BATCH_FILE_TYPE', 'value': 'zip'},
                {'name': 'CURL_CA_BUNDLE', 'value': '/etc/ssl/certs/ca-certificates.crt'},
            ],
            'vcpus': 1,
            'memory': 1024,
        },
        'retryStrategy': {
            'attempts': 1
        },
    }

    # Create client.
    batch = boto3.client('batch', region_name='eu-central-1')

    # Push training collection job.
    job['jobName'] = 'export-{}'.format(project_id)
    job['containerOverrides']['command'] = ['export.py']
    job['containerOverrides']['memory'] = 1024
    job['containerOverrides']['vcpus'] = 1

    if batch_array_size > 1:
        job['arrayProperties'] = {'size': batch_array_size}

    current_job = batch.submit_job(**job)
    all_jobs.append(current_job)

{x['jobId']: x['status'] for x in batch.describe_jobs(jobs=[job['jobId'] for job in all_jobs])['jobs']}
