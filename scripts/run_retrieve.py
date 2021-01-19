import datetime
import logging

import numpy
from PIL import Image

from pixels.retrieve import retrieve
from pixels.search import search_data

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

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
                "coordinates": [
                    [
                        [-1028560.0, 4689560.0],
                        [-1028560.0, 4680000.0],
                        [-1020000.0, 4680000.0],
                        [-1020000.0, 4689560.0],
                        [-1028560.0, 4689560.0],
                    ]
                ],
            },
        },
    ],
}


# Search scenes
result = search_data(geojson, start="2020-07-01", end="2020-07-15", maxcloud=50)
scene = result[0]

# Get pixels.
now = datetime.datetime.now()
stack = [
    retrieve(scene["bands"][band], geojson, scale=10, clip=True)
    for band in ["B04", "B03", "B02"]
]
print("Timing", datetime.datetime.now() - now)

# Convert to image for visualization.
# img = numpy.dstack([255 * (numpy.clip(dat[1], 0, 40000) / 40000) for dat in stack]).astype('uint8')    # Sentinel_2
img = numpy.dstack(
    [255 * (numpy.clip(dat[1], 0, 3000) / 3000) for dat in stack]
).astype(
    "uint8"
)  # Landsat_8
img = Image.fromarray(img)
img.show()
print(img)

# Ls - with low values -> without normalization
# img = numpy.dstack([dat[1] for dat in stack])
# img = Image.fromarray(img)
# img.show()
# print(img)
