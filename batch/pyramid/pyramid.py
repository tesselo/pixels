#!/usr/bin/env python3

import json
import logging
import os

import boto3
from tile_range import tile_range

from pixels import core, utils

# General log setup.
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.WARNING,
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Get logger and set info level for this one.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get path from env.
project_id = os.environ.get("PIXELS_PROJECT_ID")

bucket = os.environ.get("AWS_S3_BUCKET", "tesselo-pixels-results")
tile_group_size = int(os.environ.get("TILE_GROUP_SIZE", 50))

# Get batch index from env.
array_index = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", 0))

# Fetch config.
s3 = boto3.client("s3")
config = s3.get_object(Bucket=bucket, Key=project_id + "/config.json")
config = json.loads(config["Body"].read())

# Enforce ZIP format.
config["format"] = "ZIP"

# Compute tile index from config.
tiles = []
counter = 0
zoom = 14

for geom in config["geom"]["features"]:
    zoom = 14
    for x, y, intersection in tile_range(geom, zoom, intersection=True):
        tiles.append({"z": zoom, "x": x, "y": y, "geom": intersection})
        # Track interection counts.
        if counter % 500 == 0:
            logger.info("Counted {}".format(counter))
        counter += 1

logger.info("Found {} tiles".format(len(tiles)))

# Select the single tile to work in this iteration.
for i in range(
    array_index * tile_group_size, min(len(tiles), (array_index + 1) * tile_group_size)
):
    # Get tile by index.
    tile = tiles[i]

    # Prepare pixels query dict.
    config["geom"] = {
        "type": "Feature",
        "crs": "EPSG:3857",
        "geometry": {
            "type": tile["geom"].geom_type,
        },
    }
    if tile["geom"].geom_type == "Polygon":
        config["geom"]["geometry"]["coordinates"] = [list(tile["geom"].exterior.coords)]
    elif tile["geom"].geom_type == "MultiPolygon":
        config["geom"]["geometry"]["coordinates"] = [
            [list(dat.exterior.coords)] for dat in tile["geom"].geoms
        ]
    else:
        raise ValueError("Geom type {} not supported".format(tile["geom"].geom_type))

    # Add override to ensure target raster is full tile (important at edge).
    scale = utils.tile_scale(zoom)
    tbounds = utils.tile_bounds(tile["z"], tile["x"], tile["y"])

    config["target_geotransform"] = {
        "width": 256,
        "height": 256,
        "scale_x": scale,
        "skew_x": 0.0,
        "origin_x": tbounds[0],
        "skew_y": 0.0,
        "scale_y": -scale,
        "origin_y": tbounds[3],
    }

    logger.info("Working on tile {z}/{x}/{y}".format(**tile))

    # Verify config.
    config = utils.validate_configuration(config)

    # Get pixels data as zip file.
    output = core.handler(config)

    # Upload result to bucket.
    s3.put_object(
        Bucket=bucket,
        Key="{project_id}/tiles/{z}/{x}/{y}/pixels.zip".format(
            project_id=project_id,
            **tile,
        ),
        Body=output,
    )
