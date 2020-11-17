#!/usr/bin/env python3
import io
import json
import logging
import os
import tempfile
import zipfile

import boto3
import numpy
import rasterio
from rasterio import Affine
from rasterio.warp import Resampling
from tile_range import tile_range

from pixels import const, utils

# Get logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get path from env.
project_id = os.environ.get('PIXELS_PROJECT_ID')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
tile_group_size = int(os.environ.get('TILE_GROUP_SIZE', 2))
zoom = int(os.environ.get('TILE_ZOOM', 13))

# Get batch index from env.
array_index = int(os.environ.get('AWS_BATCH_JOB_ARRAY_INDEX', 0))

# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

# Compute tile index from config.
tiles = []
counter = 0
for geom in config['geom']['features']:
    for x, y in tile_range(geom, zoom, intersection=False):
        tiles.append({'z': zoom, 'x': x, 'y': y})
        # Track interection counts.
        if counter % 500 == 0:
            logger.info('Counted {}'.format(counter))
        counter += 1

logger.info('Found {} tiles'.format(len(tiles)))

# Select the single tile to work in this iteration.
for i in range(array_index * tile_group_size, min(len(tiles), (array_index + 1) * tile_group_size)):
    # Get tile by index.
    tile = tiles[i]
    logger.info('Aggregating tile {}'.format(tile))

    # Compute source and target creation args for aggregation.
    scale = utils.tile_scale(zoom)
    tbounds = utils.tile_bounds(zoom, tile['x'], tile['y'])
    target_creation_args = {
        'driver': 'GTiff',
        'dtype': 'uint16',
        'nodata': 0.0,
        'width': 256,
        'height': 256,
        'count': 1,
        'crs': 'epsg:3857',
        'transform': Affine(scale, 0.0, tbounds[0], 0.0, -scale, tbounds[3]),
    }
    scale_src = scale = utils.tile_scale(zoom + 1)
    source_creation_args = {
        'driver': 'GTiff',
        'dtype': 'uint16',
        'nodata': 0.0,
        'width': 256 * 4,
        'height': 256 * 4,
        'count': 1,
        'crs': 'epsg:3857',
        'transform': Affine(scale_src, 0.0, tbounds[0], 0.0, -scale_src, tbounds[3]),
    }
    # Compute children indices for this tile.
    children = (
        (zoom + 1, tile['x'] * 2, tile['y'] * 2),
        (zoom + 1, tile['x'] * 2 + 1, tile['y'] * 2),
        (zoom + 1, tile['x'] * 2, tile['y'] * 2 + 1),
        (zoom + 1, tile['x'] * 2 + 1, tile['y'] * 2 + 1),
    )
    # Create list of files to put into zip files.
    children_data = {}
    for index, child in enumerate(children):
        try:
            fl = s3.get_object(Bucket=const.BUCKET, Key='{}/tiles/{}/{}/{}/pixels.zip'.format(project_id, child[0], child[1], child[2]))
        except:
            continue
        with zipfile.ZipFile(io.BytesIO(fl['Body'].read())) as zf:
            for band in zf.namelist():
                # Ignore non-tif files.
                if not band.endswith('.tif'):
                    continue
                elif band not in children_data:
                    # Instantiate childrend data array.
                    children_data[band] = [None, None, None, None]
                with rasterio.open(io.BytesIO(zf.read(band))) as rst:
                    children_data[band][index] = rst.read(1)

    # Write all timesteps into a single zipfile.
    logger.info('Packaging data into zip file.')
    output = tempfile.NamedTemporaryFile()
    with zipfile.ZipFile(output.name, 'w') as zf:
        for band, child in children_data.items():
            target_array = numpy.zeros((256 * 4, 256 * 4))
            for index, data in enumerate(child):
                if data is None:
                    continue
                x_index = index % 2
                y_index = int(index > 1)
                target_array = target_array.astype(data.dtype)
                target_array[y_index * 256: (y_index + 1) * 256, x_index * 256: (x_index + 1) * 256] = data

            target_creation_args['dtype'] = str(target_array.dtype)
            source_creation_args['dtype'] = str(target_array.dtype)

            with rasterio.io.MemoryFile() as memfile_src:
                with rasterio.io.MemoryFile() as memfile_tar:
                    with memfile_src.open(**source_creation_args) as src:
                        src.write(target_array.reshape(1, target_array.shape[0], target_array.shape[1]))
                        with memfile_tar.open(**target_creation_args) as tar:
                            rasterio.warp.reproject(rasterio.band(src, 1), rasterio.band(tar, 1), resampling=Resampling.cubic)
                    # Add file to zip.
                    memfile_tar.seek(0)
                    zf.writestr(band, memfile_tar.read())

    # Upload result to bucket.
    s3.put_object(
        Bucket=bucket,
        Key='{project_id}/tiles/{z}/{x}/{y}/pixels.zip'.format(
            project_id=project_id,
            **tile,
        ),
        Body=output,
    )
