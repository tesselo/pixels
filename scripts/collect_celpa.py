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

from pixels.const import LS_BANDS, LS_PLATFORMS, NODATA_VALUE, S2_BANDS
from pixels.mosaic import composite, latest_pixel_s2, latest_pixel_s2_stack
from pixels.retrieve import retrieve
from pixels import search
from pixels.utils import compute_wgs83_bbox, timeseries_steps

logging.basicConfig(level=logging.INFO)

# AOI
geojson = {
    "type": "FeatureCollection",
    "name": "m_grande",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-1006608.126849290914834, 4823706.554369583725929],
                    [-1006608.126849290914834, 4855094.944302001968026],
                    [-985360.601356576895341, 4855094.944302001968026],
                    [-985360.601356576895341, 4823706.554369583725929],
                    [-1006608.126849290914834, 4823706.554369583725929],
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
    start='2017-08-01',
    end='2020-08-31',
    interval='years',
    scale=10,
    clip=True,
    maxcloud=10,
    limit=5,
    bands=['B4', 'B3', 'B2'],
    platforms= LS_PLATFORMS
)

stack = result[0][1]
print('Timing', datetime.datetime.now() - now)
#print(stack)

# Convert to image for visualization.
img = numpy.dstack([255 * (numpy.clip(dat, 0, 40000) / 40000) for dat in [stack[2], stack[1], stack[0]]]).astype('uint8')    #Landsat case
img = Image.fromarray(img)
img.show()
#img.save('/home/keren/projects/API_Images/tests/1.png', 'PNG')
print(img)


# # Years_list
# years = [*range(2000, 2021, 1)]
# filenames = [f"img_{year}_08_01.txt" for year in years_list]