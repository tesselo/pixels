#!/usr/bin/env python3

import json
import logging
import math
import os

import boto3
import mercantile
from rasterio.features import bounds
from shapely.geometry import Polygon, shape

from pixels import utils

# Get logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'florence-s2')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
tile_group_size = int(os.environ.get('TILE_GROUP_SIZE', 50))

# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

# Compute tile index from config.
current_job = None
all_jobs = []
for zoom in range(14, -1, -1):
    tiles = []
    counter = 0
    for geom in config['geom']['features']:
        # Compute tile range.
        geombounds = bounds(utils.reproject_feature(geom, 'EPSG:4326'))
        minimumTile = mercantile.tile(geombounds[0], geombounds[3], zoom)
        maximumTile = mercantile.tile(geombounds[2], geombounds[1], zoom)
        # Instanciate
        geom_shape = shape(utils.reproject_feature(geom, 'EPSG:3857')['geometry'])
        print(minimumTile, maximumTile)
        for x in range(minimumTile.x, maximumTile.x + 1):
            for y in range(minimumTile.y, maximumTile.y + 1):
                # Compute tile bounds.
                tbounds = utils.tile_bounds(zoom, x, y)
                # Instanciate tile polygon.
                tile = Polygon([
                    [tbounds[0], tbounds[1]],
                    [tbounds[2], tbounds[1]],
                    [tbounds[2], tbounds[3]],
                    [tbounds[0], tbounds[3]],
                    [tbounds[0], tbounds[1]],
                ])
                # Compute intersection geometry.
                intersection = tile.intersection(geom_shape)
                if intersection:
                    tiles.append({'z': zoom, 'x': x, 'y': y, 'geom': intersection})
                # Track interection counts.
                if counter % 500 == 0:
                    print('Counted', counter, tbounds)
                counter += 1

    nr_of_tiles = len(tiles)
    batch_array_size = math.ceil(nr_of_tiles / tile_group_size)

    print('Found {} tiles - array size is {} - tile group size is {}'.format(nr_of_tiles, batch_array_size, tile_group_size))

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
                {'name': 'TILE_GROUP_SIZE', 'value': str(tile_group_size)},
                {'name': 'AWS_S3_BUCKET', 'value': bucket},
                {'name': 'BATCH_FILE_S3_URL', 'value': 's3://tesselo-pixels-scripts/batch.zip'},
                {'name': 'BATCH_FILE_TYPE', 'value': 'zip'},
                {'name': 'CURL_CA_BUNDLE', 'value': '/etc/ssl/certs/ca-certificates.crt'},
                {'name': 'TILE_ZOOM', 'value': str(zoom)},
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
    job['jobName'] = 'pyramid-{}'.format(project_id)
    job['containerOverrides']['command'] = ['pyramid.py' if zoom == 14 else 'pyramid_up.py']
    job['containerOverrides']['memory'] = 1024 * 2 if zoom == 14 else 1014
    job['containerOverrides']['vcpus'] = 2 if zoom == 14 else 1
    if batch_array_size > 1:
        job['arrayProperties'] = {'size': batch_array_size}
    if current_job is not None:
        job['dependsOn'] = [
            {'jobId': current_job['jobId']},
        ]
    current_job = batch.submit_job(**job)
    all_jobs.append(current_job)

{x['jobId']: x['status'] for x in batch.describe_jobs(jobs=[job['jobId'] for job in all_jobs])['jobs']}
