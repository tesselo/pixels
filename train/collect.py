#!/usr/bin/env python3

import io
import json
import logging
import os

import boto3
import numpy

from pixels import core, utils

# Get logger.
logger = logging.getLogger(__name__)

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'test')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')

# Get batch index from env.
geom_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))

# Get prediction flag from env.
train_or_predict = 'predict' if os.environ.get('PREDICT', 'False').lower() == 'true' else 'train'

# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

# Check for data.
if train_or_predict not in config:
    raise ValueError('{} geojson needs to be present.'.format(train_or_predict))

# Enforce NPZ format.
config['format'] = 'NPZ'

# Compute timesteps from config.
steps = [dat for dat in utils.timeseries_steps(config['start'], config['end'], config['interval'], config['interval_step'])]

# Get geom collection.
# Get relevant collection and remove both from config, they are not required for
# the pixel grabber.
geom_collection = config[train_or_predict]
config.pop('train')
config.pop('predict')

# Loop through steps.
results = []
for step in steps:
    logger.info('Working on geom {}, step {}'.format(geom_index, step))
    # Get geom from index.
    geom = geom_collection['features'][geom_index]
    if 'properties' not in geom:
        geom['properties'] = {}
    geom['properties']['geom_index'] = geom_index

    # Add geom to config so that the parser is happy.
    config['geom'] = geom

    # Update start and end dates from step.
    config['start'] = str(step[0].date())
    config['end'] = str(step[1].date())

    # Verify config.
    config = utils.validate_configuration(config)

    # Get pixels.
    data = core.handler(config)
    data = dict(numpy.load(data, allow_pickle=True))

    # Exctract class id from geom properties.
    class_name = geom['properties'].get('class', None)

    # Combine the numpy arrays.
    bands = numpy.array(list(data[band].ravel() for band in config['bands']))

    # Remove nodata, assuming nodata is zero.
    if train_or_predict == 'train':
        bands = bands[:, bands.all(axis=0)]

    # Store result.
    results.append(bands)

# Make a sanity check for the shape of the collected data.
if len(set([x['bands'].shape for x in results])) > 1:
    print('Failed packing for geom', geom_index, set([x['bands'].shape for x in results]))

# Reshape data to RNN input structure (pixels x timesteps x bands).
results = numpy.array(results)
results = numpy.swapaxes(results.T, 1, 2)

# Store data.
output = io.BytesIO()
numpy.savez_compressed(output, class_name=class_name, geom_index=geom_index, data=results)
output.seek(0)

# Upload result to bucket.
s3.put_object(
    Bucket=bucket,
    Key='{project_id}/{train_or_predict}/pixels_{geom_index}.npz'.format(
        project_id=project_id,
        train_or_predict=train_or_predict,
        geom_index=geom_index,
    ),
    Body=output,
)
