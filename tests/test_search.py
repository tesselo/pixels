import datetime
import json
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from pixels.const import L1_DATES, L2_DATES, L3_DATES, L4_DATES, L5_DATES, L7_DATES, L8_DATES
from pixels.search import search_data

#1
# Mock data for sentinel 2
sentinel_2_data_mock= MagicMock(return_value=[{
    "product_id": "S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319",
    "granule_id": "L2A_T29SND_A019940_20201230T112446",
    "sensing_time": "2020-12-30T11:30:27.462",
    "mgrs_tile": "29SND",
    "cloud_cover": 0.954463,
    "base_url": "gs://gcp-public-data-sentinel-2/L2/tiles/29/S/ND/S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319.SAFE"
}])

s2_expected_scene = {
        "product_id": "S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319",
        "granule_id": "L2A_T29SND_A019940_20201230T112446",
        "sensing_time": "2020-12-30T11:30:27.462",
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
# Empty rsult
empty_data_mock = MagicMock(return_value=[])

# Mock data for landsat 1.
l1_data_mock = MagicMock(return_value=[{
    "product_id": "LM01_L1TP_220032_19760909_20200624_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1976, 9, 9, 9, 57, 10, 37009),
    "mgrs_tile": None,
    "cloud_cover": Decimal("4.0"),
    "base_url": "gs://gcp-public-data-landsat/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2"
}])

l1_expected_scene ={
    "product_id": "LM01_L1TP_220032_19760909_20200624_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1976, 9, 9, 9, 57, 10, 37009),
    "mgrs_tile": None,
    "cloud_cover": 4.0,
    "base_url": "gs://gcp-public-data-landsat/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_BQA.TIF"
    }
}
# Mock data for landsat 2.
l2_data_mock = MagicMock(return_value=[{
    "product_id": "LM02_L1TP_219033_19781118_20180421_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1978, 11, 18, 10, 17, 24, 92000),
    "mgrs_tile": None,
    "cloud_cover": Decimal("0.0"),
    "base_url": "gs://gcp-public-data-landsat/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2"
}])

l2_expected_scene = {
    "product_id": "LM02_L1TP_219033_19781118_20180421_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1978, 11, 18, 10, 17, 24, 92000),
    "mgrs_tile": None,
    "cloud_cover": 0.0,
    "base_url": "gs://gcp-public-data-landsat/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_BQA.TIF"
    }
}
# Mock data for landsat 3.
l3_data_mock = MagicMock(return_value=[{
    "product_id": "LM03_L1TP_220033_19780830_20180421_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1978, 8, 30, 10, 39, 5, 44000),
    "mgrs_tile": None,
    "cloud_cover": Decimal("19.0"),
    "base_url": "gs://gcp-public-data-landsat/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2"
}])

l3_expected_scene = {
    "product_id": "LM03_L1TP_220033_19780830_20180421_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1978, 8, 30, 10, 39, 5, 44000),
    "mgrs_tile": None,
    "cloud_cover": 19.0,
    "base_url": "gs://gcp-public-data-landsat/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_BQA.TIF"
    }
}
# Mock data for landsat 4.
l4_data_mock = MagicMock(return_value=[{
    "product_id": "LT04_L1TP_204033_19901222_20170129_01_T1",
    "granule_id": None,
    "sensing_time": datetime.datetime(1990, 12, 22, 10, 39, 28, 254000),
    "mgrs_tile": None,
    "cloud_cover": Decimal("0.0"),
    "base_url": "gs://gcp-public-data-landsat/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1"
}])

l4_expected_scene = {
    "product_id": "LT04_L1TP_204033_19901222_20170129_01_T1",
    "granule_id": None,
    "sensing_time": datetime.datetime(1990, 12, 22, 10, 39, 28, 254000),
    "mgrs_tile": None,
    "cloud_cover": 0.0,
    "base_url": "gs://gcp-public-data-landsat/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_BQA.TIF"
    }
}
# Mock data for landsat 5.
l5_data_mock = MagicMock(return_value=[{
    "product_id": "LM05_L1TP_204032_20121226_20180522_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(2012, 12, 26, 10, 49, 51, 36007),
    "mgrs_tile": None,
    "cloud_cover": Decimal("0.0"),
    "base_url": "gs://gcp-public-data-landsat/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2"
}])

l5_expected_scene = {
    "product_id": "LM05_L1TP_204032_20121226_20180522_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(2012, 12, 26, 10, 49, 51, 36007),
    "mgrs_tile": None,
    "cloud_cover": 0.0,
    "base_url": "gs://gcp-public-data-landsat/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_BQA.TIF"
    }
}
# Mock data for landsat 7.
l7_data_mock =MagicMock(return_value=[{
    "product_id": "LE07_L1TP_204032_20201224_20201224_01_RT",
    "granule_id": None,
    "sensing_time": datetime.datetime(2020, 12, 24, 10, 33, 7, 503406),
    "mgrs_tile": None,
    "cloud_cover": Decimal("3.0"),
    "base_url": "gs://gcp-public-data-landsat/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT"
}])

l7_expected_scene = {
    "product_id": "LE07_L1TP_204032_20201224_20201224_01_RT",
    "granule_id": None,
    "sensing_time": datetime.datetime(2020, 12, 24, 10, 33, 7, 503406),
    "mgrs_tile": None,
    "cloud_cover": 3.0,
    "base_url": "gs://gcp-public-data-landsat/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_BQA.TIF"
    }
}

# Mock data for landsat 8.
l8_data_mock = MagicMock(return_value=[{
    "product_id": "LC08_L1TP_205032_20201121_20201122_01_RT",
    "granule_id": None,
    "sensing_time": datetime.datetime(2020, 11, 21, 11, 20, 37, 137788),
    "mgrs_tile": None,
    "cloud_cover": Decimal("0.01"),
    "base_url": "gs://gcp-public-data-landsat/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT"
}])

l8_expected_scene = {
    "product_id": "LC08_L1TP_205032_20201121_20201122_01_RT",
    "granule_id": None,
    "sensing_time": datetime.datetime(2020, 11, 21, 11, 20, 37, 137788),
    "mgrs_tile": None,
    "cloud_cover": 0.01,
    "base_url": "gs://gcp-public-data-landsat/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_B11.TIF",
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_BQA.TIF"
    }
}

# AOI.
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

class SearchTest(unittest.TestCase):
    @patch("pixels.search.engine.execute", sentinel_2_data_mock)
    def test_result_sentinel(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=20,
            limit=1,
            level="L2A",
            platforms="SENTINEL_2")
        self.assertDictEqual(actual[0], s2_expected_scene)

    @patch("pixels.search.engine.execute", empty_data_mock)
    def test_level(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=20,
            limit=1,
            level="L3",
            platforms="SENTINEL_2") 
        self.assertEqual(actual, [])

    @patch("pixels.search.engine.execute", empty_data_mock)
    def test_date(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_1") 
        self.assertEqual(actual, [])
        # Raise error Wrong date

    @patch("pixels.search.engine.execute", empty_data_mock)
    def test_platform(self):
        actual = search_data(
            geojson,
            start="2020-12-01",
            end="2021-01-01",
            maxcloud=20,
            limit=1,
            platforms="Landsat_1") 
        self.assertEqual(actual, [])

    @patch("pixels.search.engine.execute", l1_data_mock)
    def test_result_l1(self):
        actual = search_data(
            geojson,
            start=L1_DATES[0],
            end=L1_DATES[1],
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_1") 
        self.assertDictEqual(actual[0], l1_expected_scene)

    
    @patch("pixels.search.engine.execute", l2_data_mock)
    def test_result_l2(self):
        actual = search_data(
            geojson,
            start=L2_DATES[0],
            end=L2_DATES[1],
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_2") 
        self.assertDictEqual(actual[0], l2_expected_scene)
    
    @patch("pixels.search.engine.execute", l3_data_mock)
    def test_result_l3(self):
        actual = search_data(
            geojson,
            start=L3_DATES[0],
            end=L3_DATES[1],
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_3") 
        self.assertDictEqual(actual[0], l3_expected_scene)

    @patch("pixels.search.engine.execute", l4_data_mock)
    def test_result_l4(self):
        actual = search_data(
            geojson,
            start=L4_DATES[0],
            end=L4_DATES[1],
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_4") 
        self.assertDictEqual(actual[0], l4_expected_scene)
        # self.assertRaises = Raise ValueError -> testar os erros
        # Raise error worng platform format, should be string in uppercase separeted by _

    @patch("pixels.search.engine.execute", l5_data_mock)
    def test_result_l5(self):
        actual = search_data(
            geojson,
            start=L5_DATES[0],
            end=L5_DATES[1],
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_5") 
        self.assertDictEqual(actual[0], l5_expected_scene)

    @patch("pixels.search.engine.execute", l7_data_mock)
    def test_result_l7(self):
        actual = search_data(
            geojson,
            start=L7_DATES,
            end="2020-12-31",
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_7") 
        self.assertDictEqual(actual[0], l7_expected_scene) 

    @patch("pixels.search.engine.execute", l8_data_mock)
    def test_result_l8(self):
        actual = search_data(
            geojson,
            start=L8_DATES,
            end="2020-12-31",
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_8") 
        self.assertDictEqual(actual[0], l8_expected_scene) 
        # Run pytest show entire diff.
       
    