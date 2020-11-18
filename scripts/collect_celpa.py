
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

from pixels import search_img
from pixels.mosaic import composite, latest_pixel_s2, latest_pixel_s2_stack
from pixels.retrieve import retrieve
from pixels.search_img import get_bands
from pixels.utils import compute_wgs83_bbox, timeseries_steps

# criar geojson para marinha grande
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

#years
years_list  = [*range(2000, 2021, 1)]

filenames = [f"img_{year}_08_01.txt" for year in years_list]



result = latest_pixel_s2_stack( geojson,
    start = '2000-08-01',
    end ='2020-08-30',
    scale = 10,
    interval=years,
    bands=['B4','B3','B2'],
    limit=10,
    clip=True,
    pool=False )

print(result)

