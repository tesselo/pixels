import datetime
import os
import unittest
from unittest import mock

import numpy

from pixels.const import LANDSAT_1_LAUNCH_DATE
from pixels.exceptions import PixelsException
from pixels.mosaic import (
    calculate_start_date,
    configure_pixel_stack,
    first_valid_pixel,
    process_search_images,
)
from tests.scenarios import sample_geojson


def mock_search_data(input):
    response = []
    if input.platforms == ["SENTINEL_2"]:
        bands = {
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
        }
    else:
        bands = {
            "B1": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
            "B2": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
            "qa_pixel": os.path.join(os.path.dirname(__file__), "data/SCL.tif"),
        }

    for i in range(3):
        response.append(
            {
                "id": "S2A_MSIL2A_20200130T112311_{}".format(i),
                "sensing_time": datetime.datetime(2020, 1, 20 + i, 11, 30, 39, 918000),
                "cloud_cover": 70.091273,
                "bands": bands,
            },
        )

    if input.platforms == ["SENTINEL_2"]:
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
                platforms="SENTINEL_2",
                maxcloud=100,
            )

        # Test regular latest pixel.
        creation_args, first_end_date, stack = first_valid_pixel(
            self.geojson,
            end_date="2020-02-01",
            scale=500,
            bands=["B01", "B02"],
            clip=False,
            platforms="SENTINEL_2",
            maxcloud=100,
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
            platforms="SENTINEL_2",
            maxcloud=100,
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
            platforms="SENTINEL_2",
            maxcloud=100,
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
            platforms="SENTINEL_2",
            maxcloud=100,
        )
        self.assertEqual(first_end_date, "2020-01-20")
        expected = [[[2956, 2996], [7003, 7043]], [[2956, 2996], [7003, 7043]]]
        numpy.testing.assert_array_equal(stack, expected)

    def test_pixel_stack(self):
        # Test weekly latest pixel stack.
        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=500,
            interval="weeks",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            platforms="SENTINEL_2",
            maxcloud=100,
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
        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-01",
            scale=500,
            interval="all",
            bands=["B01", "B02"],
            clip=False,
            level="L2A",
            platforms="SENTINEL_2",
            maxcloud=100,
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
            bands=["B01", "B02", "B04", "B08"],
            clip=False,
            level="L2A",
            mode="composite",
            composite_method="SCL",
            platforms="SENTINEL_2",
            maxcloud=100,
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
        expected = [
            [[[1453, 1475, 1500], [3714, 3737, 3762], [6214, 6237, 6262]]] * 4
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
            bands=["B01", "B02", "B04", "B08"],
            clip=False,
            level="L2A",
            mode="composite",
            composite_method="SCL",
            platforms="SENTINEL_2",
            maxcloud=100,
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

    def test_pixel_stack_composite_qa_pixel(self):
        funk, search_configurations = configure_pixel_stack(
            geojson=self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=250,
            interval="weeks",
            interval_step=1,
            bands=["B1", "B2"],
            clip=False,
            level="L2",
            mode="composite",
            composite_method="QA_PIXEL",
            platforms="LANDSAT_8",
            maxcloud=100,
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
        expected = [
            [[[1453, 1475, 1500], [3714, 3737, 3762], [6214, 6237, 6262]]] * 2
        ] * 4
        numpy.testing.assert_array_equal(stack, expected)

    def test_pixel_stack_composite_full(self):
        # Test weekly latest pixel stack.
        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=250,
            interval="weeks",
            interval_step=1,
            bands=["B01", "B02", "B04", "B08"],
            clip=False,
            level="L2A",
            mode="composite",
            composite_method="FULL",
            platforms="SENTINEL_2",
            maxcloud=100,
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
        expected = [
            [[[1453, 1475, 1500], [3714, 3737, 3762], [6214, 6237, 6262]]] * 4
        ] * 4
        numpy.testing.assert_array_equal(stack, expected)
        # Test weekly latest pixel stack.
        funk, search_configurations = configure_pixel_stack(
            self.geojson,
            start="2020-01-01",
            end="2020-02-02",
            scale=250,
            interval="weeks",
            interval_step=1,
            bands=["B01", "B02", "B04", "B08", "SCL"],
            clip=False,
            level="L2A",
            mode="composite",
            composite_method="FULL",
            platforms="SENTINEL_2",
            maxcloud=100,
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
        expected = [
            [[[1453, 1475, 1500], [3714, 3737, 3762], [6214, 6237, 6262]]] * 4
            + [[[7, 6, 7], [8, 5, 7], [5, 7, 5]]]
        ] * 4
        numpy.testing.assert_array_equal(stack, expected)
