#!/usr/bin/env python3

import io
import json
import logging
import os

import boto3
import fiona
import numpy

from pixels.mosaic import latest_pixel_s2_stack

logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger('botocore').setLevel(logging.ERROR)
logging.getLogger('rasterio').setLevel(logging.ERROR)


def collect():
    # Setup boto client.
    s3 = boto3.client('s3')

    # Get setup variables from env.
    bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
    project_id = os.environ.get('PIXELS_PROJECT_ID', 'test')
    local_path = os.environ.get('PIXELS_LOCAL_PATH', None)
    array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))
    features_per_job = int(os.environ.get('BATCH_FEATURES_PER_JOB', 100))
    logger.info('Bucket {} | Project {} | ArrayIndex {} | FeatPerJob {}'.format(
        bucket, project_id, array_index, features_per_job
    ))

    if local_path:
        with open(os.path.join(local_path, 'config.json')) as fl:
            config = json.load(fl)
    else:
        # Fetch config.
        config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
        config = json.loads(config['Body'].read())

    # Select feature set for this job.
    geofile = config['training_geofile']
    if local_path:
        geo_object = os.path.join(local_path, geofile)
    else:
        geo_object = s3.get_object(Bucket=bucket, Key=project_id + '/{}'.format(geofile))['Body']

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
            geojson=feature,
            start=config['min_date'],
            end=config['max_date'],
            scale=config['scale'],
            interval=config['interval'],
            bands=config['bands'],
            limit=config['limit'],
            clip=config['clip'],
            maxcloud=config.get('max_cloud_cover', None),
        )

        # Combine data into numpy array.
        output = io.BytesIO()
        numpy.savez_compressed(output, feature=feature, array_index=array_index, data=[dat[2] for dat in result], dates=[dat[1] for dat in result], creation_args=result[0][0])
        output.seek(0)

        # Upload result to bucket.
        if local_path:
            target = os.path.join(local_path, 'training/pixels{}.npz'.format(feature['features'][0]['id']))
            with open(target, 'wb') as fl:
                fl.write(output.read())
        else:
            s3.put_object(
                Bucket=bucket,
                Key='{project_id}/training/pixels_{fid}.npz'.format(
                    project_id=project_id,
                    fid=feature['features'][0]['id'],
                ),
                Body=output,
            )


if __name__ == '__main__':
    collect()
