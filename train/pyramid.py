#!/usr/bin/env python3

import json
import logging
import os

import boto3
from rasterio.features import bounds
from shapely.geometry import Polygon, shape

from pixels import core, utils

# Get logger.
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'clftests')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
tile_group_size = int(os.environ.get('TILE_GROUP_SIZE', 100))

# Get batch index from env.
array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))

# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

# Enforce ZIP format.
config['format'] = 'ZIP'

# Compute tile index from config.
tiles = []
counter = 0
zoom = 14

for geom in config['geom']['features']:
    # Compute tile range.
    geombounds = bounds(utils.reproject_feature(geom, 'EPSG:4326'))
    zoom = 14
    minimumTile = utils.tile_index(geombounds[0], geombounds[3], zoom)
    maximumTile = utils.tile_index(geombounds[2], geombounds[1], zoom)
    # Instanciate
    geom_shape = shape(utils.reproject_feature(geom, 'EPSG:3857')['geometry'])
    logger.info('{} - {}'.format(minimumTile, maximumTile))
    for x in range(minimumTile[0], maximumTile[0] + 1):
        for y in range(minimumTile[1], maximumTile[1] + 1):
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
                logger.info('Counted {} {}'.format(counter, tbounds))
            counter += 1

logger.info('Found {} tiles'.format(len(tiles)))

# Select the single tile to work in this iteration.
for i in range(array_index * tile_group_size, min(len(tiles), (array_index + 1) * tile_group_size)):
    # Get tile by index.
    tile = tiles[i]

    # Prepare pixels query dict.
    config["geom"] = {
        "type": "Feature",
        "crs": "EPSG:3857",
        "geometry": {
            "type": tile['geom'].geom_type,
        },
    }
    if tile['geom'].geom_type == 'Polygon':
        config["geom"]["geometry"]["coordinates"] = [list(tile['geom'].exterior.coords)]
    elif tile['geom'].geom_type == 'MultiPolygon':
        config["geom"]["geometry"]["coordinates"] = [[list(dat.exterior.coords)] for dat in tile['geom'].geoms]
    else:
        raise ValueError('Geom type {} not supported'.format(tile['geom'].geom_type))

    # Add override to ensure target raster is full tile (important at edge).
    scale = utils.tile_scale(zoom)
    tbounds = utils.tile_bounds(tile['z'], tile['x'], tile['y'])

    config['target_geotransform'] = {
        'width': 256,
        'height': 256,
        'scale_x': scale,
        'skew_x': 0.0,
        'origin_x': tbounds[0],
        'skew_y': 0.0,
        'scale_y': -scale,
        'origin_y': tbounds[3],
    }

    logger.info('Working on tile {z}/{x}/{y}'.format(**tile))

    # Verify config.
    config = utils.validate_configuration(config)

    # Get pixels data as zip file.
    output = core.handler(config)

    # Upload result to bucket.
    s3.put_object(
        Bucket=bucket,
        Key='{project_id}/tiles/{z}/{x}/{y}/pixels.zip'.format(
            project_id=project_id,
            **tile,
        ),
        Body=output,
    )
