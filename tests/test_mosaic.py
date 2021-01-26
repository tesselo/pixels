import datetime
import os
import unittest
from unittest import mock

import numpy

from pixels.mosaic import latest_pixel


def mock_search_data(
    geojson,
    start=None,
    end=None,
    platforms=None,
    maxcloud=None,
    scene=None,
    level=None,
    limit=10,
    sort="sensing_time",
):
    response = []
    for i in range(3):
        response.append(
            {
                "product_id": "S2A_MSIL2A_20200130T112311_{}".format(i),
                "granule_id": "L2A_T29SMC_A024058_20200130T112435_{}".format(i),
                "sensing_time": datetime.datetime(2020, 1, 20 + i, 11, 30, 39, 918000),
                "mgrs_tile": "29SMC",
                "cloud_cover": 70.091273,
                "base_url": "gs://data-sentinel-2/S2A_{}.SAFE".format(i),
                "bands": {
                    "B01": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B02": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                },
            },
        )

    return response


@mock.patch("pixels.mosaic.search_data", mock_search_data)
class TestMosaic(unittest.TestCase):
    def setUp(self):
        self.geojson = {
            "type": "FeatureCollection",
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
                                [-1028560.0, 4689000.0],
                                [-1028000.0, 4689560.0],
                                [-1028560.0, 4689560.0],
                            ]
                        ],
                    },
                },
            ],
        }

    def test_latest_pixel(self):
        creation_args, first_end_date, stack = latest_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=False,
        )
        self.assertEqual(first_end_date, "2020-01-20")
        expected = [[[2956, 2996], [7003, 7043]], [[2956, 2996], [7003, 7043]]]
        numpy.testing.assert_array_equal(stack, expected)

        creation_args, first_end_date, stack = latest_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=True,
        )
        expected = [[[2956, 0], [0, 0]], [[2956, 0], [0, 0]]]
        numpy.testing.assert_array_equal(stack, expected)
