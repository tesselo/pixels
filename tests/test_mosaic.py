import datetime
import os
import unittest
from unittest import mock

import numpy

from pixels.algebra import parser
from pixels.const import LANDSAT_1_LAUNCH_DATE
from pixels.exceptions import PixelsException
from pixels.mosaic import (
    calculate_start_date,
    configure_pixel_stack,
    first_valid_pixel,
    process_search_images,
)
from tests.scenarios import sample_geojson


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
    bands=None,
):
    response = []
    for i in range(3):
        response.append(
            {
                "id": "S2A_MSIL2A_20200130T112311_{}".format(i),
                "sensing_time": datetime.datetime(2020, 1, 20 + i, 11, 30, 39, 918000),
                "cloud_cover": 70.091273,
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
                    "SCL": os.path.join(os.path.dirname(__file__), "data/SCL.tif"),
                },
            },
        )
    # Append zero scene.
    response.append(
        {
            "id": "S2A_MSIL2A_20200130T112311_{}".format(i),
            "sensing_time": datetime.datetime(2020, 2, 1, 11, 30, 39, 918000),
            "cloud_cover": 70.091273,
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
                "SCL": os.path.join(os.path.dirname(__file__), "data/SCL.tif"),
            },
        },
    )
    return response


class TestStartDates(unittest.TestCase):
    def test_start_date_bad_format(self):
        with self.assertRaisesRegex(PixelsException, "Invalid end date"):
            calculate_start_date("the beginning of all times")

    def test_start_date_string(self):
        calculated_date = calculate_start_date("2022-01-31")
        self.assertEqual(calculated_date, "2021-12-31")

    def test_start_date_datetime(self):
        calculated_date = calculate_start_date(datetime.datetime(2022, 1, 31))
        self.assertEqual(calculated_date, "2021-12-31")

    def test_start_date_date(self):
        calculated_date = calculate_start_date(datetime.date(2022, 1, 31))
        self.assertEqual(calculated_date, "2021-12-31")

    def test_start_date_list(self):
        calculated_date = calculate_start_date(["one", "two", "three"])
        self.assertEqual(calculated_date, LANDSAT_1_LAUNCH_DATE)

    def test_start_date_tuple(self):
        calculated_date = calculate_start_date(("one", "two", "three"))
        self.assertEqual(calculated_date, LANDSAT_1_LAUNCH_DATE)


@mock.patch("pixels.mosaic.search_data", mock_search_data)
class TestMosaic(unittest.TestCase):
    def setUp(self):
        self.geojson = sample_geojson

    def test_first_valid_pixel(self):
        # Test bad date
        with self.assertRaisesRegex(PixelsException, "Invalid end date"):
            first_valid_pixel(
                self.geojson,
                end_date="the beginning of all times",
                scale=500,
                bands=["B01", "B02"],
                clip=False,
            )

        # Test regular latest pixel.
        creation_args, first_end_date, stack = first_valid_pixel(
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
        creation_args, first_end_date, stack = first_valid_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=True,
        )
        expected = [[[2956, 0], [0, 0]], [[2956, 0], [0, 0]]]
        numpy.testing.assert_array_equal(stack, expected)
        # Test with pool.
        creation_args, first_end_date, stack = first_valid_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=False,
            pool_bands=True,
        )
        self.assertEqual(first_end_date, "2020-01-20")
        expected = [[[2956, 2996], [7003, 7043]], [[2956, 2996], [7003, 7043]]]
        numpy.testing.assert_array_equal(stack, expected)
        # Test with cloud sorting.
        creation_args, first_end_date, stack = first_valid_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=False,
            pool_bands=True,
            sort="cloud_cover",
        )
        self.assertEqual(first_end_date, "2020-01-20")
        expected = [[[2956, 2996], [7003, 7043]], [[2956, 2996], [7003, 7043]]]
        numpy.testing.assert_array_equal(stack, expected)

    def test_pixel_stack(self):
        # Test weekly latest pixel stack.
        """
        creation_args, dates, stack = pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=500,
            interval="weeks",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=5,
        )"""
        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=500,
            interval="weeks",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=5,
        )
        dates = []
        stack = []
        for search in search_configurations:
            creation_args, date, img = process_search_images(funk, search)
            dates.append(date)
            stack.append(img)

        dates = [f for f in dates if f is not None]
        stack = [f for f in stack if f is not None]

        self.assertEqual(
            dates, ["2020-01-20", "2020-01-20", "2020-01-20", "2020-01-20"]
        )
        expected = [[[[2956, 2996], [7003, 7043]]] * 2] * 4
        numpy.testing.assert_array_equal(stack, expected)

        # Test all latest pixel.
        """
        creation_args, dates, stack = pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-01",
            scale=500,
            interval="all",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=1,
        )"""
        funk, search_configurations = configure_pixel_stack(
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
        dates = []
        stack = []
        for search in search_configurations:
            creation_args, date, img = process_search_images(funk, search)
            dates.append(date)
            stack.append(img)
        dates = [f for f in dates if f is not None]
        stack = [f for f in stack if f is not None]

        self.assertEqual(dates, ["2020-01-20", "2020-01-21", "2020-01-22"])
        expected = [[[[2956, 2996], [7003, 7043]]] * 2] * 3
        numpy.testing.assert_array_equal(stack, expected)

    def test_pixel_stack_composite(self):
        # Test weekly latest pixel stack.

        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=250,
            interval="weeks",
            interval_step=1,
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=1,
            mode="composite",
            composite_method="SCL",
        )
        dates = []
        stack = []
        for search in search_configurations:
            creation_args, date, img = process_search_images(funk, search)
            dates.append(date)
            stack.append(img)
        dates = [f for f in dates if f is not None]
        stack = [f for f in stack if f is not None]

        self.assertEqual(
            dates, ["2020-01-20", "2020-01-20", "2020-01-20", "2020-01-20"]
        )
        # expected = [[[[2956, 2996], [7003, 7043]]] * 2] * 4
        expected = [
            [[[1453, 1475, 1500], [3714, 3737, 3762], [6214, 6237, 6262]]] * 2
        ] * 4
        numpy.testing.assert_array_equal(stack, expected)
        # Interval step 2 reduces number of layers to 2.

        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=500,
            interval="weeks",
            interval_step=2,
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            pool_size=1,
            mode="composite",
        )
        dates = []
        stack = []
        for search in search_configurations:
            creation_args, date, img = process_search_images(funk, search)
            dates.append(date)
            stack.append(img)
        dates = [f for f in dates if f is not None]
        stack = [f for f in stack if f is not None]
        self.assertEqual(dates, ["2020-01-20", "2020-01-20"])

    def test_algebra(self):
        # Test regular latest pixel.
        bands = ["B01", "B02"]
        creation_args, first_end_date, stack = first_valid_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=bands,
            clip=False,
        )
        ndvi = parser.evaluate("(B01 + 2 * B02) / (B01 + B02)", bands, stack)
        expected = [[1.5, 1.5], [1.5, 1.5]]
        numpy.testing.assert_array_equal(ndvi, expected)
