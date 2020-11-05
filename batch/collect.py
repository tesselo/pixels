#!/usr/bin/env python3

import io
import json
import logging
import os

import boto3
import fiona
import numpy

from pixels.mosaic import latest_pixel_s2_stack

logger = logging.getLogger()
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def collect():
    # Setup boto client.
    s3 = boto3.client('s3')

    # Get setup variables from env.
    bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
    # project_id = os.environ.get('PROJECT_ID', 'test')
    project_id = 'esblidar'
    array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))
    features_per_job = int(os.environ.get('BATCH_FEATURES_PER_JOB', 10))
    logger.info('Bucket {} | Project {} | ArrayIndex {} | FeatPerJob {}'.format(
        bucket, project_id, array_index, features_per_job
    ))

    # Fetch config.
    config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
    config = json.loads(config['Body'].read())

    # Select feature for this job.
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


if __name__ == '__main__':
    collect()
