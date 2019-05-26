#!/usr/bin/env python3

import io
import json
import os

import boto3
import numpy

SENTINEL_2_BANDS = [
    'B01',
    'B02',
    'B03',
    'B04',
    'B05',
    'B06',
    'B07',
    'B08',
    'B8A',
    'B09',
    'B10',
    'B11',
    'B12',
]

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'test')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
train_or_predict = 'predict' if os.environ.get('PREDICT', 'false').lower() == 'true' else 'train'
# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())
# Construct class lookup.
classes = [feat['properties']['class'] for feat in config['train']['features']]
class_lookup = {cl: idx for idx, cl in enumerate(sorted(set(classes)))}
# Enforce not clipping to geom for prediction.
if train_or_predict == 'predict':
    config['clip_to_geom'] = False
# List data data files.
paginator = s3.get_paginator('list_objects')
data_files = paginator.paginate(
    Bucket=bucket,
    Prefix='{}/{}/'.format(project_id, train_or_predict),
    PaginationConfig={
        'MaxItems': 10000,
        'PageSize': 1000,
    }
)
# Fetch data
training_x = []
training_y = []
for page in data_files:
    for npz in page['Contents']:
        print(npz['Key'])
        # Download and open npz file.
        data = s3.get_object(Bucket=bucket, Key=npz['Key'])['Body'].read()
        data = dict(numpy.load(io.BytesIO(data), allow_pickle=True))
        training_x.append(data['data'])
        training_y.append(numpy.ones(data['data'].shape[0]) * class_lookup[data['class_name'].item()])

X = numpy.vstack(training_x)
Y = numpy.hstack(training_y)
Y = Y.astype('uint8')

# Store data in single npz file (used for training and re-training).
output = io.BytesIO()
to_save = {
    'X': X
}
if train_or_predict == 'train':
    to_save['Y'] = Y
numpy.savez_compressed(output, **to_save)
# Rewind buffer.
output.seek(0)
# Upload packed data to bucket.
s3.put_object(
    Bucket=bucket,
    Key='{project_id}/{train_or_predict}.npz'.format(
        project_id=project_id,
        train_or_predict=train_or_predict,
    ),
    Body=output,
)
