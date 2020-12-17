# GDAL_DISABLE_READDIR_ON_OPEN=YES CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif CPL_CURL_VERBOSE=0 ipython pixels/v1/tests/test_mosaic.py
import datetime
import logging

import matplotlib.pyplot as plt
import numpy
from PIL import Image

from pixels.mosaic import composite, latest_pixel, latest_pixel_s2_stack

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)


# center = [-1018560, 4099560]
# center = [-450862, 4941912]
# center = [1473493,-988811]
# center = [-12461810,4993243]
# center = [13311107,-2575583]
# center = [13076538,5177296]
# center = [-885576,4636573]
# center = [829312, 5933414]
# center = [15510814.0, 4328712.0]
center = [-476019, 1742667]

size = 5600

geojson = {
    "type": "FeatureCollection",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [center[0] - size / 2, center[1] - size / 2],
                        [center[0] + size / 2, center[1] - size / 2],
                        [center[0] + size / 2, center[1] + size / 2],
                        [center[0] - size / 2, center[1] + size / 2],
                        [center[0] - size / 2, center[1] - size / 2],
                    ]
                ],
            },
        },
    ],
}

# Get pixels.
now = datetime.datetime.now()

# creation_args, dates, stack = latest_pixel(geojson, end_date='2020-10-31', scale=10, clip=True, platforms=['SENTINEL_2'], bands=('B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12'))

# creation_args, stack = composite(
#     geojson,
#     start="2020-07-01",
#     end="2020-07-31",
#     scale=10,
#     maxcloud=100,
#     limit=20,
#     pool=True,
# )

args, date, stack = latest_pixel_s2_stack(
    geojson=geojson,
    start="2020-07-01",
    end="2020-07-31",
    interval="weeks",
    scale=30,
    clip=True,
    # platforms='LANDSAT_8',
    platforms="SENTINEL_2",
    # bands=("B2", "B3", "B4"),
    bands=["B02", "B03", "B04"],  # , "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
)
stack = stack[0]

print("Timing", datetime.datetime.now() - now)


plt.imshow(
    numpy.dstack(
        [(numpy.clip(dat, 0, 4000) / 4000.0) for dat in [stack[2], stack[1], stack[0]]]
    ).astype("float32")
)
plt.show()
# # Convert to image for visualization.
# img = numpy.dstack(
#     [255 * (numpy.clip(dat, 0, 4000) / 4000) for dat in [stack[2], stack[1], stack[0]]]
# ).astype("uint8")
# img = Image.fromarray(img)
# plt.imshow(img)
# plt.show()
# img.save('/home/keren/projects/API_Images/tests/1.png', 'PNG')
