import datetime
from decimal import Decimal
from unittest.mock import MagicMock

# Mock data for sentinel 2.
sentinel_2_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319",
            "granule_id": "L2A_T29SND_A019940_20201230T112446",
            "sensing_time": "2020-12-30T11:30:27.462",
            "mgrs_tile": "29SND",
            "cloud_cover": 0.954463,
            "base_url": "gs://gcp-public-data-sentinel-2/L2/tiles/29/S/ND/S2B_MSIL2A_20201230T112359_N0214_R037_T29SND_20201230T132319.SAFE",
        }
    ]
)

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
        "B12": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/S/ND/2020/12/S2B_29SND_20201230_0_L2A/B12.tif",
    },
}

# Empty rsult.
empty_data_mock = MagicMock(return_value=[])

# Mock data for landsat 1.
l1_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LM01_L1TP_220032_19760909_20200624_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1976, 9, 9, 9, 57, 10, 37009),
            "mgrs_tile": None,
            "cloud_cover": Decimal("4.0"),
            "base_url": "gs://gcp-public-data-landsat/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2",
        }
    ]
)

l1_expected_scene = {
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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/220/032/LM01_L1TP_220032_19760909_20200624_01_T2/LM01_L1TP_220032_19760909_20200624_01_T2_BQA.TIF",
    },
}
# Mock data for landsat 2.
l2_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LM02_L1TP_219033_19781118_20180421_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1978, 11, 18, 10, 17, 24, 92000),
            "mgrs_tile": None,
            "cloud_cover": Decimal("0.0"),
            "base_url": "gs://gcp-public-data-landsat/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2",
        }
    ]
)

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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/219/033/LM02_L1TP_219033_19781118_20180421_01_T2/LM02_L1TP_219033_19781118_20180421_01_T2_BQA.TIF",
    },
}
# Mock data for landsat 3.
l3_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LM03_L1TP_220033_19780830_20180421_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1978, 8, 30, 10, 39, 5, 44000),
            "mgrs_tile": None,
            "cloud_cover": Decimal("19.0"),
            "base_url": "gs://gcp-public-data-landsat/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2",
        }
    ]
)

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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/220/033/LM03_L1TP_220033_19780830_20180421_01_T2/LM03_L1TP_220033_19780830_20180421_01_T2_BQA.TIF",
    },
}
# Mock data for landsat 4.
l4_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LT04_L1TP_204033_19901222_20170129_01_T1",
            "granule_id": None,
            "sensing_time": datetime.datetime(1990, 12, 22, 10, 39, 28, 254000),
            "mgrs_tile": None,
            "cloud_cover": Decimal("0.0"),
            "base_url": "gs://gcp-public-data-landsat/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1",
        }
    ]
)

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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/204/033/LT04_L1TP_204033_19901222_20170129_01_T1/LT04_L1TP_204033_19901222_20170129_01_T1_BQA.TIF",
    },
}
# Mock data for landsat 5.
l5_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LM05_L1TP_204032_20121226_20180522_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(2012, 12, 26, 10, 49, 51, 36007),
            "mgrs_tile": None,
            "cloud_cover": Decimal("0.0"),
            "base_url": "gs://gcp-public-data-landsat/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2",
        }
    ]
)

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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM05/01/204/032/LM05_L1TP_204032_20121226_20180522_01_T2/LM05_L1TP_204032_20121226_20180522_01_T2_BQA.TIF",
    },
}
# Mock data for landsat 7.
l7_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LE07_L1TP_204032_20201224_20201224_01_RT",
            "granule_id": None,
            "sensing_time": datetime.datetime(2020, 12, 24, 10, 33, 7, 503406),
            "mgrs_tile": None,
            "cloud_cover": Decimal("3.0"),
            "base_url": "gs://gcp-public-data-landsat/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT",
        }
    ]
)

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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/204/032/LE07_L1TP_204032_20201224_20201224_01_RT/LE07_L1TP_204032_20201224_20201224_01_RT_BQA.TIF",
    },
}

# Mock data for landsat 8.
l8_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LC08_L1TP_205032_20201121_20201122_01_RT",
            "granule_id": None,
            "sensing_time": datetime.datetime(2020, 11, 21, 11, 20, 37, 137788),
            "mgrs_tile": None,
            "cloud_cover": Decimal("0.01"),
            "base_url": "gs://gcp-public-data-landsat/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT",
        }
    ]
)

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
        "BQA": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_RT/LC08_L1TP_205032_20201121_20201122_01_RT_BQA.TIF",
    },
}
