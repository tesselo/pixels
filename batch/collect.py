#!/usr/bin/env python3

import datetime
import io
import json
import logging
import os
import pickle
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool

import boto3
import fiona
import numpy
import requests
from fiona.transform import transform_geom
from PIL import Image
from satstac import Collection

from pixels.mosaic import latest_pixel_s2_stack
from pixels.retrieve import retrieve
from pixels.utils import compute_wgs83_bbox, timeseries_steps

# Get logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Setup boto client.
s3 = boto3.client('s3')

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'test')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')

# Get batch index from env.
array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))
features_per_job = int(os.environ.get('BATCH_FEATURES_PER_JOB', 10))

# Fetch config.
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())
# config = json.load(open('/home/tam/Desktop/pixels_test/config.json', 'rb'))

# Select feature for this job.
# geojson = s3.get_object(Bucket=bucket, Key=project_id + '/features.geojson')['Body']
# geojson = s3.get_object(Bucket=bucket, Key=project_id + '/mz-training-2020.gpkg')['Body']
geofile = config['training_geofile']
geo_object = s3.get_object(Bucket=bucket, Key=project_id + '/{}'.format(geofile))['Body']
# geojson = open('/home/tam/Desktop/pixels_test/mz-training-2020.gpkg', 'rb')
# if not geopath.lower().startswith('s3://'):
#     geopath = 's3://{}/{}/{}'.format(bucket, project_id, geopath)

features = []
with fiona.open(geo_object) as src:
    for index, feat in enumerate(src):
        if index in range(array_index * features_per_job, (array_index + 1) * features_per_job):
            features.append({
                "type": "FeatureCollection",
                "crs": src.crs,
                "features": [feat],
            })

for feature in features:
    # Fetch pixels.
    result = latest_pixel_s2_stack(
        feature,
        config['min_date'],
        config['max_date'],
        config['scale'],
        config['interval'],
        config['bands'],
        config['limit'],
        config['clip'],
        pool=False,
    )

    # Combine data into numpy array.
    output = io.BytesIO()
    numpy.savez_compressed(output, feature=feature, array_index=array_index, data=[dat[2] for dat in result], dates=[dat[1] for dat in result], creation_args=result[0][0])
    # numpy.savez_compressed('/home/tam/Desktop/pixels_test/pixels_{}.npz'.format(array_index), feature=feature, array_index=array_index, data=[dat[2] for dat in result], dates=[dat[1] for dat in result], creation_args=result[0][0])
    output.seek(0)

    # Upload result to bucket.
    s3.put_object(
        Bucket=bucket,
        Key='{project_id}/training/pixels_{fid}.npz'.format(
            project_id=project_id,
            fid=feature['features'][0]['id'],
        ),
        Body=output,
    )
