import unittest
from unittest.mock import patch

from pixels.search import build_query, search_data
from pixels.validators import PixelsSearchValidator
from tests.scenarios import empty_data_mock, landsat_data_mock, sentinel_2_data_mock

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
    @patch("pixels.search.execute_query", sentinel_2_data_mock)
    def test_result_sentinel(self):
        data = PixelsSearchValidator(
            geojson=geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=2,
            level="L2A",
            platforms="SENTINEL_2",
            bands=["B04", "B8A", "B02"],
        )
        actual = search_data(data)
        self.assertEqual(actual[0]["id"], "S2A_29TNG_20170128_0_L2A")
        self.assertEqual(
            actual[0]["bands"]["B8A"],
            "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B8A.tif",
        )

    @patch("pixels.search.execute_query", landsat_data_mock)
    def test_result_landsat(self):
        data = PixelsSearchValidator(
            geojson=geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=2,
            platforms=["LANDSAT_8"],
            bands=["B2", "B4", "B5"],
        )
        actual = search_data(data)
        self.assertEqual(actual[0]["id"], "LC08_L2SP_204031_20170106_20200905_02_T1_SR")
        self.assertEqual(
            actual[0]["bands"]["B5"],
            "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B5.TIF",
        )

    @patch("pixels.search.execute_query", empty_data_mock)
    def test_result_empty(self):
        data = PixelsSearchValidator(
            geojson=geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=2,
            platforms="LANDSAT_8",
            bands=["B99"],
        )

        actual = search_data(data)
        self.assertEqual(actual, [])

    def test_build_query_l1c(self):
        self.maxDiff = None
        data = PixelsSearchValidator(
            geojson=geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=2,
            platforms="SENTINEL_2",
            level="L1C",
            bands=["B01", "B02"],
        )
        query = build_query(data)
        self.assertEqual(
            query,
            "SELECT id, collection_id, datetime, properties, assets FROM data.items WHERE ST_Intersects(ST_MakeEnvelope(-48.52081457543516, -1.4848032319778461,-48.42374328200645,-1.381535093272429,4326), geometry) AND (properties ->> 'platform') IN ('sentinel-2a','sentinel-2b','sentinel-2c','sentinel-2d') AND collection_id IN ('sentinel-s2-l1c') AND datetime >= timestamp '2020-12-01' AND datetime <= timestamp '2021-01-01' AND (properties -> 'eo:cloud_cover')::float < 100 ORDER BY datetime DESC LIMIT 2",
        )

    def test_build_query_l2a(self):
        self.maxDiff = None
        data = PixelsSearchValidator(
            geojson=geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=2,
            platforms="SENTINEL_2",
            level="L2A",
            bands=["B01", "B02"],
        )
        query = build_query(data)
        self.assertEqual(
            query,
            "SELECT * FROM ( SELECT DISTINCT ON (id) * FROM ( SELECT id, collection_id, datetime, properties, assets FROM data.items WHERE ST_Intersects(ST_MakeEnvelope(-48.52081457543516, -1.4848032319778461,-48.42374328200645,-1.381535093272429,4326), geometry) AND (properties ->> 'platform') IN ('sentinel-2a','sentinel-2b','sentinel-2c','sentinel-2d') AND collection_id IN ('sentinel-s2-l2a','sentinel-s2-l2a-cogs') AND datetime >= timestamp '2020-12-01' AND datetime <= timestamp '2021-01-01' AND (properties -> 'eo:cloud_cover')::float < 100 ORDER BY id, collection_id DESC) AS s2table_distinct ) AS s2table_ordered ORDER BY datetime DESC LIMIT 2",
        )

    def test_build_query_landsat(self):
        self.maxDiff = None
        data = PixelsSearchValidator(
            geojson=geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=100,
            limit=2,
            platforms="LANDSAT_8",
            level="L2",
            bands=["B2", "B4", "B5"],
        )
        query = build_query(data)
        self.assertEqual(
            query,
            "SELECT id, collection_id, datetime, properties, assets FROM data.items WHERE ST_Intersects(ST_MakeEnvelope(-48.52081457543516, -1.4848032319778461,-48.42374328200645,-1.381535093272429,4326), geometry) AND (properties ->> 'platform') IN ('LANDSAT_8') AND collection_id IN ('landsat-c2l2-sr') AND datetime >= timestamp '2020-12-01' AND datetime <= timestamp '2021-01-01' AND (properties -> 'eo:cloud_cover')::float < 100 ORDER BY datetime DESC LIMIT 2",
        )
