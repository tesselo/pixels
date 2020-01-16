#!/usr/bin/env python3

import io
import json
import logging
import os
import tempfile

import boto3

import geopandas
from geodaisy import GeoObject
from pixels import core, utils

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
tile_group_size = int(os.environ.get('TILE_GROUP_SIZE', 20))
start = os.environ.get('START_DATE', '2019-05-01')
end = os.environ.get('END_DATE', '2019-05-31')

# Get batch index from env.
array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))

# Fetch geoms.
dir = tempfile.mkdtemp()
s3 = boto3.client('s3')
src = os.path.join(dir, filename)
s3.download_file(Bucket=bucket, Key=project_id + '/' + filename, Filename=src)

#src = '/home/tam/Desktop/pge_buf200ft_ca/pge_buff200_placer.gpkg'

# Open geographic file.
pge_buf200_placer_df = geopandas.read_file(src)

# Setup target files.
header = None
result = []

# Loop through rows and call pixels.
for index, row in pge_buf200_placer_df.iloc[(array_index * tile_group_size):((array_index + 1) * tile_group_size)].iterrows():
    logger.info('Working on feature ID {}'.format(index))
    config = {
        'start': start,
        'end': end,
        'platform': 'Sentinel-2',
        'product_type': 'S2MSI1C',
        'max_cloud_cover_percentage': 60,
        'mode': 'latest_pixel',
        'color': False,
        'format': 'CSV',
        'delay': False,
        'scale': 10,
        'bands': [
            'B02',
            'B03',
            'B04',
            'B05',
            'B06',
            'B07',
            'B08',
            'B8A',
            'B11',
            'B12',
        ],
        'formulas': [
            {'name': 'NDVI', 'expression': '(B08 - B04) / (B08 + B04)'},
        ],
        'clip_to_geom': True,
        'clip_all_touched': False,
        'geom': {
            'type': 'Feature',
            'crs': pge_buf200_placer_df.crs['init'],
            'properties': {
                'line_segid': row['line_segid'],
            },
            'geometry': json.loads(GeoObject(row['geometry']).geojson()),
        },
    }

    # Verify config.
    config = utils.validate_configuration(config)
    # Get pixels data as zip file.
    output = core.handler(config)
    # Convert to string by row.
    data = output.read().decode().split('\n')
    # Compare headers to ensure consistency.
    if not header:
        header = data[0]
    elif header != data[0]:
        raise ValueError('Inconsistent headers found in csv files.')
    # Add data rows to result list, skipping header and empty last line.
    result += data[1:-1]

# Remove rows with nan NDVI values.
result = [row for row in result if ',nan' not in row]

# Combine all rows to one large file.
result = '\n'.join([header] + result)

#with open('/home/tam/Desktop/bla.csv', 'w') as fl:
#    fl.write(result)

# Upload result to bucket.
with io.BytesIO(bytes(result, 'utf-8')) as output:
    s3.put_object(
        Bucket=bucket,
        Key='{project_id}/exports/result_{start}_{end}_{idx}.csv'.format(
            project_id=project_id,
            start=start,
            end=end,
            idx=array_index,
        ),
        Body=output,
    )
