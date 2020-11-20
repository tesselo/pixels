import datetime
import logging
import pickle
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool

import fiona
import numpy
import rasterio
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
#creation_args, stack = latest_pixel_s2(geojson, end_date='2020-10-31', scale=10, clip=True, bands=('B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12'), pool=True)


result = latest_pixel_s2(geojson=geojson, end_date='2020-01-31', scale=10, clip=True, maxcloud=30, limit=10, bands=['B4','B3', 'B2'], platforms= 'LANDSAT_8')

print('Timing', datetime.datetime.now() - now)
#Convert img
creation_args = result[0]
stack = numpy.array(result[2])
creation_args['count'] = 3

# Convert to img
#img = numpy.dstack([255 * (numpy.clip(dat, 0, 100000) / 100000) for dat in [stack[2], stack[1], stack[0]]]).astype('uint8')
# #img = numpy.dstack([dat for dat in [stack[2], stack[1], stack[0]]]).astype('uint8')    # Without normalization
# # img = Image.fromarray(img)
# # img.show()
# # print(img)
# # Save 
# # img.save(f"/home/keren/projects/API_Images/tests/{result[1]}.png", 'PNG')

# Save raster as tif file
height = creation_args['height']
width = creation_args['width']


with rasterio.open(f"/home/keren/projects/API_Images/tests/{result[1]}.tif",'w',**creation_args) as dst:
    dst.write(stack)    

