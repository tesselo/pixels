import datetime
import json
import logging
import os

import boto3
import mercantile
import numpy
import pyproj
import rasterio
from shapely.geometry import mapping, shape
from shapely.ops import transform
from supermercado.burntiles import burn

from pixels.clouds import pixels_mask
from pixels.mosaic import latest_pixel_s2_stack

logging.basicConfig(level=logging.WARNING)

s3 = boto3.client("s3")

bucket = os.environ.get("AWS_S3_BUCKET", "tesselo-pixels-results")
project_id = os.environ.get("PIXELS_PROJECT_ID", "test")

config = s3.get_object(Bucket=bucket, Key=project_id + "/config.json")
config = json.loads(config["Body"].read())

model = None

studyarea = {
    "type": "FeatureCollection",
    "name": "aoi_lx_3857",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [4221106.735919824, -1736265.598606449],
                        [4193357.887847751, -1872923.001226717],
                        [4193357.887847751, -1872923.001226717],
                        [4168839.871963011, -2000260.921782380],
                        [4059250.149940649, -2146427.525249328],
                        [3957791.871378712, -2192621.624387202],
                        [3908895.935608357, -2423814.498744275],
                        [3746235.752146748, -2382705.686221981],
                        [3736327.010446677, -2426564.146185098],
                        [3575745.634752777, -2380980.764413798],
                        [3645024.390525834, -2029048.342937532],
                        [3805756.588984016, -2064205.766222333],
                        [3849309.791841074, -1842019.460616930],
                        [4026940.635842372, -1881828.503819331],
                        [4071817.876159736, -1710962.181728938],
                        [4221106.735919824, -1736265.598606449],
                    ]
                ],
            },
        },
    ],
}

src_crs = pyproj.CRS("EPSG:3857")
dst_crs = pyproj.CRS("EPSG:4326")

project = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True).transform
rep = transform(project, shape(studyarea["features"][0]["geometry"]))
rep = mapping(rep)
rep = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": rep,
        },
    ],
}

total = len([i for i, (x, y, z) in enumerate(burn(rep["features"], 11))])

for i, (x, y, z) in enumerate(burn(rep["features"], 11)):
    print("At {} out of {} - ({}, {}, {})".format(i, total, z, x, y))
    now = datetime.datetime.now()
    bounds = mercantile.xy_bounds(x, y, z)
    geojson = {
        "type": "FeatureCollection",
        "crs": {"init": "EPSG:3857"},
        "features": [mercantile.feature((x, y, z), projected="mercator")],
    }
    zoom_level_14_scale = 9.554628535654047
    result = latest_pixel_s2_stack(
        geojson,
        config["min_date"],
        config["max_date"],
        zoom_level_14_scale,
        config["interval"],
        config["bands"],
        config["limit"],
        clip=False,
        pool=False,
    )

    X = numpy.array([dat[2] for dat in result])
    X = X.swapaxes(0, 2).swapaxes(1, 3)
    X = X.reshape(X.shape[0] * X.shape[1], X.shape[2], X.shape[3])

    cloud_mask = pixels_mask(
        X[:, :, 8],
        X[:, :, 7],
        X[:, :, 6],
        X[:, :, 2],
        X[:, :, 1],
        X[:, :, 0],
        X[:, :, 9],
    )
    X[cloud_mask] = 0

    Y_predicted = model.predict(X)
    Y_predicted = numpy.argmax(Y_predicted, axis=1) + 1

    creation_args = result[0][0]
    Y_predicted = Y_predicted.reshape(
        1, creation_args["height"], creation_args["width"]
    ).astype("uint16")

    with rasterio.open(
        "/home/tam/Desktop/pixels_test/nonseq_zxy/prediction_{}_{}_{}.tif".format(
            z, x, y
        ),
        "w",
        **creation_args
    ) as dst:
        dst.write(Y_predicted)

    print(datetime.datetime.now() - now)
