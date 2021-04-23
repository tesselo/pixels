import datetime
import os
import unittest
from unittest import mock

import numpy

from pixels.algebra import parser
from pixels.mosaic import latest_pixel, latest_pixel_stack


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
    sensor=None,
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
                    "B03": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B04": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B05": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B06": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B07": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B08": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B8A": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B09": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B10": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B11": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                    "B12": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                },
            },
        )
    # Append zero scene.
    response.append(
        {
            "product_id": "S2A_MSIL2A_20200130T112311_{}".format(i),
            "granule_id": "L2A_T29SMC_A024058_20200130T112435_{}".format(i),
            "sensing_time": datetime.datetime(2020, 2, 1, 11, 30, 39, 918000),
            "mgrs_tile": "29SMC",
            "cloud_cover": 70.091273,
            "base_url": "gs://data-sentinel-2/S2A_{}.SAFE".format(i),
            "bands": {
                "B01": os.path.join(os.path.dirname(__file__), "data/B02.tif"),
                "B02": os.path.join(os.path.dirname(__file__), "data/B02.tif"),
                "B03": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B04": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B05": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B06": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B07": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B08": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B8A": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B09": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B10": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B11": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
                "B12": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
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
        # Test regular latest pixel.
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
        # Test with clip.
        creation_args, first_end_date, stack = latest_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=True,
        )
        expected = [[[2956, 0], [0, 0]], [[2956, 0], [0, 0]]]
        numpy.testing.assert_array_equal(stack, expected)
        # Test with pool.
        creation_args, first_end_date, stack = latest_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=False,
            pool=True,
        )
        self.assertEqual(first_end_date, "2020-01-20")
        expected = [[[2956, 2996], [7003, 7043]], [[2956, 2996], [7003, 7043]]]
        numpy.testing.assert_array_equal(stack, expected)

    def test_latest_pixel_stack(self):
        # Test weekly latest pixel stack.
        creation_args, dates, stack = latest_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=500,
            interval="weeks",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=1,
        )
        self.assertEqual(
            dates, ["2020-01-20", "2020-01-20", "2020-01-20", "2020-01-20"]
        )
        expected = [[[[2956, 2996], [7003, 7043]]] * 2] * 4
        numpy.testing.assert_array_equal(stack, expected)

        # Test all latest pixel.
        creation_args, dates, stack = latest_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-01",
            scale=500,
            interval="all",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=1,
        )
        self.assertEqual(dates, ["2020-01-20", "2020-01-21", "2020-01-22"])
        expected = [[[[2956, 2996], [7003, 7043]]] * 2] * 3
        numpy.testing.assert_array_equal(stack, expected)

    def test_latest_pixel_stack_composite(self):
        # Test weekly latest pixel stack.
        creation_args, dates, stack = latest_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=500,
            interval="weeks",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=1,
            mode="composite",
        )
        self.assertEqual(
            dates, ["2020-01-20", "2020-01-20", "2020-01-20", "2020-01-20"]
        )
        expected = [[[[2956, 2996], [7003, 7043]]] * 7] * 4
        numpy.testing.assert_array_equal(stack, expected)

    def test_algebra(self):
        # Test regular latest pixel.
        bands = ["B01", "B02"]
        creation_args, first_end_date, stack = latest_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=bands,
            clip=False,
        )
        ndvi = parser.evaluate("(B01 + 2 * B02) / (B01 + B02)", bands, stack)
        expected = [[1.5, 1.5], [1.5, 1.5]]
        numpy.testing.assert_array_equal(ndvi, expected)
