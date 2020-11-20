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

from pixels import search
from pixels.const import LS_BANDS, LS_PLATFORMS, NODATA_VALUE, S2_BANDS
from pixels.mosaic import composite, latest_pixel_s2, latest_pixel_s2_stack
from pixels.retrieve import retrieve
from pixels.search import get_bands
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
                    [-1018560.0, 4689560.0],
                    [-1018560.0, 4685000.0],
                    [-1014000.0, 4685000.0],
                    [-1014000.0, 4689560.0],
                    [-1018560.0, 4689560.0],
                ]]
            }
        },
    ]
}

# Get pixels.
now = datetime.datetime.now()
# creation_args, stack = latest_pixel_s2(geojson, end_date='2020-10-31', scale=10, clip=True, bands=('B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12'), pool=True)
result = latest_pixel_s2_stack(
    geojson=geojson,
    start='2020-10-01',
    end='2020-10-31',
    interval='months',
    scale=10,
    clip=True,
    bands=('B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12'),
)
stack = result[0][2]
print('Timing', datetime.datetime.now() - now)

# Convert to image for visualization.
img = numpy.dstack([255 * (numpy.clip(dat, 0, 4000) / 4000) for dat in [stack[2], stack[1], stack[0]]]).astype('uint8')    #Landsat case
img = Image.fromarray(img)
img.show()
# img.save('/home/keren/projects/API_Images/tests/1.png', 'PNG')
