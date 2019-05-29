#!/usr/bin/env python3

import json
import os

import boto3

# Get path from env.
# project_id = os.environ.get('PROJECT_ID', 'test')
project_id = 'celpa_2years'
# project_id = 'test'
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')

# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

# Compute nr of jobs from config.
nr_of_geoms_train = len(config['train']['features'])
nr_of_geoms_predict = len(config['predict']['features'])

# Setup the job dict.
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

all_jobs = []

# Push training collection job.
job['jobName'] = 'collect-train-{}'.format(project_id)
job['containerOverrides']['command'] = ['collect.py']
job['arrayProperties'] = {'size': nr_of_geoms_train}
# collect_train_result = batch.submit_job(**job)
# all_jobs.append(collect_train_result)

# Push training pack job.
job['jobName'] = 'pack-train-{}'.format(project_id)
job['containerOverrides']['command'] = ['pack.py']
job.pop('arrayProperties', None)
# job['dependsOn'] = [
#     {'jobId': collect_train_result['jobId'], 'type': 'SEQUENTIAL'},
# ]
# pack_train_result = batch.submit_job(**job)
# all_jobs.append(pack_train_result)

# Push training job.
job['jobName'] = 'train-{}'.format(project_id)
job['containerOverrides']['command'] = ['train.py']
job['containerOverrides']['memory'] = 4096
job.pop('arrayProperties', None)
# job['dependsOn'] = [
#     {'jobId': pack_train_result['jobId'], 'type': 'SEQUENTIAL'},
# ]
# train_job = batch.submit_job(**job)
# all_jobs.append(train_job)

# Push prediction collection job (assumes only one geom for prediction).
job['jobName'] = 'collect-predict-{}'.format(project_id)
job['containerOverrides']['command'] = ['collect.py']
job['containerOverrides']['environment'].append({'name': 'PREDICT', 'value': 'true'})
job['containerOverrides']['memory'] = 4096
job.pop('arrayProperties', None)
job.pop('dependsOn', None)
collect_predict_job = batch.submit_job(**job)
all_jobs.append(collect_predict_job)

# Push predict pack job.
job['jobName'] = 'pack-predict-{}'.format(project_id)
job['containerOverrides']['command'] = ['pack.py']
job['containerOverrides']['memory'] = 4096
job.pop('arrayProperties', None)
job['dependsOn'] = [
    {'jobId': collect_predict_job['jobId'], 'type': 'SEQUENTIAL'},
]
pack_predict_job = batch.submit_job(**job)
all_jobs.append(pack_predict_job)

# Push prediction job.
job['jobName'] = 'predict-{}'.format(project_id)
job['containerOverrides']['command'] = ['train.py']
job['containerOverrides']['memory'] = 4096
job.pop('arrayProperties', None)
job['dependsOn'] = [
    # {'jobId': train_job['jobId'], 'type': 'SEQUENTIAL'},
    {'jobId': pack_predict_job['jobId'], 'type': 'SEQUENTIAL'},
]
predict_job = batch.submit_job(**job)
all_jobs.append(predict_job)

{x['jobName']: x['status'] for x in batch.describe_jobs(jobs=[dat['jobId'] for dat in all_jobs])['jobs']}
