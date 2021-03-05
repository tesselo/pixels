import unittest
from unittest.mock import MagicMock, patch

from pixels.search import search_data
import json

# Setup mock data for S2 search.

expected_scene ={
        "product_id": "S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319",
        "granule_id": "L2A_T29SND_A019940_20201230T112446",
        "sensing_time": "2020-12-30T11:30:27.46",
        "mgrs_tile": "29SND",
        "cloud_cover": 0.954463,
        "base_url": "gs://gcp-public-data-sentinel-2/L2/tiles/29/S/ND/S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319.SAFE",
        "bands": {
            "B01": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B01.tif",
            "B02": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B02.tif",
            "B03": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B03.tif",
            "B04": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B04.tif",
            "B05": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B05.tif",
            "B06": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B06.tif",
            "B07": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B07.tif",
            "B08": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B08.tif",
            "B8A": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B8A.tif",
            "B10": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B10.tif",
            "B09": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B09.tif",
            "B11": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B11.tif",
            "B12": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B12.tif"
        }
    }

sentinel_2_data_mock= MagicMock(return_value=[{
    "product_id": "S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319",
    "granule_id": "L2A_T29SND_A019940_20201230T112446",
    "sensing_time": "2020-12-30T11:30:27.462",
    "mgrs_tile": "29SND",
    "cloud_cover": 0.954463,
    "base_url": "gs://gcp-public-data-sentinel-2/L2/tiles/29/S/ND/S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319.SAFE"
}])

# criar um mock para cada situação

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

class SentinelSearchTest(unittest.TestCase):
    @patch("pixels.search.engine.execute", sentinel_2_data_mock)
    def test_result(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=20,
            limit=1,
            level="L2A",
            platforms="SENTINEL_2")
        self.assertDictEqual(actual[0], expected_scene)

    @patch("pixels.search.engine.execute", sentinel_2_data_mock)
    def test_wrong_level(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=20,
            limit=1,
            level="L3A",
            platforms="SENTINEL_2") 
        self.assertEqual(actual, [])

       
        # Run pytest show entire diff.
        # Create different scenarios and test different outputs.
        # self.assertRaises = Raise ValueError -> testar os erros
        # SetUp data setup different for each test.