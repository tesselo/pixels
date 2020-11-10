# GDAL_DISABLE_READDIR_ON_OPEN=YES CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif CPL_CURL_VERBOSE=0 ipython pixels/v1/tests/test_mosaic.py
import datetime
import logging
import pickle
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool

import fiona
import numpy
import requests
from fiona.transform import transform_geom
from PIL import Image
from satstac import Collection

from pixels.mosaic import latest_pixel_s2
from pixels.retrieve import retrieve
from pixels.utils import compute_wgs83_bbox, timeseries_steps
from pixels import search_img

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


# Get pixels.
now = datetime.datetime.now()
stack = latest_pixel_s2(geojson, '2020-08-01', scale=10, clip=True, bands=['B04', 'B03', 'B02'])
print('Timing', datetime.datetime.now() - now)

# Convert to image for visualization.
img = numpy.dstack([255 * (numpy.clip(dat, 0, 4000) / 4000) for dat in stack[2]]).astype('uint8')
img = Image.fromarray(img)
img.show()
