import unittest
from unittest.mock import patch

from pixels.const import (
    L1_DATES,
    L2_DATES,
    L3_DATES,
    L4_DATES,
    L5_DATES,
    L7_DATES,
    L8_DATES,
)
from pixels.search import search_data
from tests.scenarios import (
    empty_data_mock,
    l1_data_mock,
    l1_expected_scene,
    l2_data_mock,
    l2_expected_scene,
    l3_data_mock,
    l3_expected_scene,
    l4_data_mock,
    l4_expected_scene,
    l5_data_mock,
    l5_expected_scene,
    l7_data_mock,
    l7_expected_scene,
    l8_data_mock,
    l8_expected_scene,
    l8_l2_data_mock,
    l8_l2_expected_scene,
    s2_expected_scene,
    sentinel_2_data_mock,
)

# AOI.
geojson = {
    "type": "FeatureCollection",
    "name": "Belém",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-5401312.371412288397551, -165306.043231031770119],
                        [-5401312.371412288397551, -153806.687808195129037],
                        [-5390506.444457160308957, -153806.687808195129037],
                        [-5390506.444457160308957, -165306.043231031770119],
                        [-5401312.371412288397551, -165306.043231031770119],
                    ]
                ],
            },
        },
    ],
}


geojson_MZ = {
    "type": "FeatureCollection",
    "name": "TEST_AREA_MNC_PIXELS",
    "crs": {"init": "EPSG:32736"},
    "features": [
        {
            "type": "Feature",
            "properties": {"id": 4, "areas_pred": "Area Manica Sul"},
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [452589.846835004282184, 7701177.79016338288784],
                            [452589.846835004282184, 7768612.886005393229425],
                            [521878.828473358182237, 7768612.886005393229425],
                            [521878.828473358182237, 7701177.79016338288784],
                            [452589.846835004282184, 7701177.79016338288784],
                        ]
                    ]
                ],
            },
        }
    ],
}


class SearchTest(unittest.TestCase):
    maxDiff = None

    @patch("pixels.search.conn_pixels.execute", sentinel_2_data_mock)
    def test_result_sentinel(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=1,
            level="L2A",
            platforms="SENTINEL_2",
        )
        self.assertDictEqual(actual[0], s2_expected_scene)

    @patch("pixels.search.conn_pixels.execute", empty_data_mock)
    def test_level(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=1,
            level="L3",
            platforms="SENTINEL_2",
        )
        self.assertEqual(actual, [])

    @patch("pixels.search.conn_pixels.execute", empty_data_mock)
    def test_date(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_1",
        )
        self.assertEqual(actual, [])

    @patch("pixels.search.conn_pixels.execute", empty_data_mock)
    def test_platform(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=1,
            platforms="Landsat_1",
        )
        self.assertEqual(actual, [])

    @patch("pixels.search.conn_pixels.execute", l1_data_mock)
    def test_result_l1(self):
        actual = search_data(
            geojson,
            start=L1_DATES[0],
            end=L1_DATES[1],
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_1",
        )
        self.assertDictEqual(actual[0], l1_expected_scene)

    @patch("pixels.search.conn_pixels.execute", l2_data_mock)
    def test_result_l2(self):
        actual = search_data(
            geojson,
            start=L2_DATES[0],
            end=L2_DATES[1],
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_2",
        )
        self.assertDictEqual(actual[0], l2_expected_scene)

    @patch("pixels.search.conn_pixels.execute", l3_data_mock)
    def test_result_l3(self):
        actual = search_data(
            geojson,
            start=L3_DATES[0],
            end=L3_DATES[1],
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_3",
        )
        self.assertDictEqual(actual[0], l3_expected_scene)

    @patch("pixels.search.conn_pixels.execute", l4_data_mock)
    def test_result_l4(self):
        actual = search_data(
            geojson,
            start=L4_DATES[0],
            end=L4_DATES[1],
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_4",
        )
        self.assertDictEqual(actual[0], l4_expected_scene)

    @patch("pixels.search.conn_pixels.execute", l5_data_mock)
    def test_result_l5(self):
        actual = search_data(
            geojson,
            start=L5_DATES[0],
            end=L5_DATES[1],
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_5",
        )
        self.assertDictEqual(actual[0], l5_expected_scene)

    @patch("pixels.search.conn_pixels.execute", l7_data_mock)
    def test_result_l7(self):
        actual = search_data(
            geojson,
            start=L7_DATES,
            end="2020-01-31",
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_7",
        )
        self.assertDictEqual(actual[0], l7_expected_scene)

    @patch("pixels.search.conn_pixels.execute", l8_data_mock)
    def test_result_l8(self):
        actual = search_data(
            geojson,
            start=L8_DATES,
            end="2021-01-31",
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_8",
        )
        self.assertDictEqual(actual[0], l8_expected_scene)

    @patch("pixels.search.conn_pxsearch.execute", l8_l2_data_mock)
    def test_result_ls_l2(self):
        actual = search_data(
            geojson_MZ,
            start=L8_DATES,
            end="2015-03-01",
            maxcloud=100,
            limit=1,
            platforms="LANDSAT_8",
            level="L2",
        )
        self.assertDictEqual(actual[0], l8_l2_expected_scene)
