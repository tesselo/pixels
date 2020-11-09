import datetime
import logging
import pickle
from multiprocessing import Pool

import fiona
import numpy
import requests
from fiona.transform import transform_geom
from PIL import Image

from pixels.mosaic import latest_pixel_s2
from pixels.retrieve import retrieve
from pixels.utils import compute_wgs83_bbox, timeseries_steps

logging.basicConfig(level=logging.INFO)

geojson = {
    "type": "FeatureCollection",
    "name": "aoi_lx_3857",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-1028560.0, 4689560.0],
                    [-1028560.0, 4689000.0],
                    [-1028000.0, 4689000.0],
                    [-1028000.0, 4689560.0],
                    [-1028560.0, 4689560.0],
                ]]
            }
        },
    ]
}

import logging
# Search scenes.
import os

logging.basicConfig(level=logging.DEBUG)
# os.environ["AWS_REQUEST_PAYER"] = "requester"
search = {
    "limit": 10,
    "intersects": compute_wgs83_bbox(geojson),
    "datetime": "2019-08-01T00:00:00Z/2019-08-31T00:00:00Z",
    "collections": ['sentinel-s2-l2a-cogs'],
}
endpoint = 'https://earth-search.aws.element84.com/v0/search'
response = requests.post(endpoint, json=search).json()
scenes = response['features']
scene = scenes[0]

# Get pixels.
now = datetime.datetime.now()
stack = [retrieve(scene['assets'][band]['href'], geojson, scale=10, clip=True) for band in ['B04', 'B03', 'B02']]
print('Timing', datetime.datetime.now() - now)

# Convert to image for visualization.
img = numpy.dstack([255 * (numpy.clip(dat[1], 0, 4000) / 4000) for dat in stack]).astype('uint8')
img = Image.fromarray(img)
# img.show()
print(img)
