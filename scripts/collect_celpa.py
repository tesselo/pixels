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
                "coordinates": [
                    [
                        [-1006608.126849290914834, 4823706.554369583725929],
                        [-1006608.126849290914834, 4855094.944302001968026],
                        [-985360.601356576895341, 4855094.944302001968026],
                        [-985360.601356576895341, 4823706.554369583725929],
                        [-1006608.126849290914834, 4823706.554369583725929],
                    ]
                ],
            },
        },
    ],
}


# Get pixels.
now = datetime.datetime.now()

result = latest_pixel_s2_stack(
    geojson=geojson,
    start="2020-01-01",
    end="2020-01-31",
    interval="months",
    scale=10,
    clip=True,
    maxcloud=30,
    limit=5,
    bands=["B04", "B03", "B02"],
    platforms="SENTINEL_2",
)

for index, scene in enumerate(result):
    stack = scene[2]
    img = numpy.dstack(
        [
            255 * (numpy.clip(dat, 0, 4000) / 4000)
            for dat in [stack[2], stack[1], stack[0]]
        ]
    ).astype("uint8")
    # img = numpy.dstack([dat for dat in [stack[2], stack[1], stack[0]]]).astype('uint8')    # Without normalization
    img = Image.fromarray(img)
    # img.show()
    img.save(f"/home/keren/projects/API_Images/tests/{scene[1]}.png", "PNG")
    print(f"{index+1} of {len(result)} saved")
    # print(img)

# # Years_list
# years = [*range(2000, 2021, 1)]
# filenames = [f"img_{year}_08_01.png" for year in years]
