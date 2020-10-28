#!/usr/bin/env python3

import glob
import io
import json
import os

import boto3
import h5py
import numpy
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential, load_model, model_from_json
from rasterio.io import MemoryFile

from pixels import utils


# Setup boto client.
s3 = boto3.client('s3')
# Fetch all data to memory.
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
project_id = os.environ.get('PROJECT_ID', 'test')
# config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
# config = json.loads(config['Body'].read())
paginator = s3.get_paginator('list_objects_v2')
pages = paginator.paginate(
    Bucket=bucket,
    Prefix='{}/training/'.format(project_id),
)
result = []
# for page in pages:
#     for obj in page['Contents']:
#         print(obj['Size'])
#         data = s3.get_object(
#             Bucket=bucket,
#             Key=obj['Key']
#         )['Body'].read()
#         data = numpy.load(io.BytesIO(data), allow_pickle=True)
#         result.append(data)
Xs = []
Ys = []
for path in glob.glob('/home/tam/Desktop/pixels_test/pixels_data/*.npz'):
    with open(path, 'rb') as fl:
        data = numpy.load(fl, allow_pickle=True)
        X = data['data']
        X = X.swapaxes(0, 2).swapaxes(1, 3)
        X = X.reshape(X.shape[0] * X.shape[1], X.shape[2], X.shape[3])
        Xs.append(X)
        Ys.append(data['feature'].item()['features'][0]['properties']['Class'])
Xs = numpy.vstack(Xs)
Ys = numpy.vstack(Ys).flatten()
