import datetime
from unittest.mock import MagicMock

# Mock data for sentinel 2.
sentinel_2_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "SENTINEL_2",
            "sensor_id": None,
            "product_id": "S2A_MSIL2A_20201211T134211_N0214_R124_T22MGD_20201211T160214",
            "granule_id": "L2A_T22MGD_A028578_20201211T134207",
            "sensing_time": datetime.datetime(2020, 12, 11, 13, 42, 43, 997000),
            "mgrs_tile": "22MGD",
            "cloud_cover": 11.373496,
            "wrs_path": 85217265,
            "wrs_row": 85217265,
            "base_url": "gs://gcp-public-data-sentinel-2/L2/tiles/22/M/GD/S2A_MSIL2A_20201211T134211_N0214_R124_T22MGD_20201211T160214.SAFE",
        }
    ]
)

s2_expected_scene = {
    "spacecraft_id": "SENTINEL_2",
    "sensor_id": None,
    "product_id": "S2A_MSIL2A_20201211T134211_N0214_R124_T22MGD_20201211T160214",
    "granule_id": "L2A_T22MGD_A028578_20201211T134207",
    "sensing_time": datetime.datetime(2020, 12, 11, 13, 42, 43, 997000),
    "mgrs_tile": "22MGD",
    "cloud_cover": 11.373496,
    "wrs_path": 85217265,
    "wrs_row": 85217265,
    "base_url": "gs://gcp-public-data-sentinel-2/L2/tiles/22/M/GD/S2A_MSIL2A_20201211T134211_N0214_R124_T22MGD_20201211T160214.SAFE",
    "bands": {
        "B01": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B01.tif",
        "B02": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B02.tif",
        "B03": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B03.tif",
        "B04": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B04.tif",
        "B05": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B05.tif",
        "B06": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B06.tif",
        "B07": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B07.tif",
        "B08": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B08.tif",
        "B8A": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B8A.tif",
        "B09": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B09.tif",
        "B11": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B11.tif",
        "B12": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/B12.tif",
        "SCL": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22/M/GD/2020/12/S2A_22MGD_20201211_0_L2A/SCL.tif",
    },
}
# Empty rsult.
empty_data_mock = MagicMock(return_value=[])

# Mock data for landsat 1.
l1_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_1",
            "sensor_id": "MSS",
            "product_id": "LM01_L1TP_240061_19730313_20180427_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1973, 3, 13, 12, 57, 5, 41000),
            "mgrs_tile": None,
            "cloud_cover": 26.0,
            "wrs_path": 240,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LM01/01/240/061/LM01_L1TP_240061_19730313_20180427_01_T2",
        }
    ]
)


l1_expected_scene = {
    "spacecraft_id": "LANDSAT_1",
    "sensor_id": "MSS",
    "product_id": "LM01_L1TP_240061_19730313_20180427_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1973, 3, 13, 12, 57, 5, 41000),
    "mgrs_tile": None,
    "cloud_cover": 26.0,
    "wrs_path": 240,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LM01/01/240/061/LM01_L1TP_240061_19730313_20180427_01_T2",
    "bands": {
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/240/061/LM01_L1TP_240061_19730313_20180427_01_T2/LM01_L1TP_240061_19730313_20180427_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/240/061/LM01_L1TP_240061_19730313_20180427_01_T2/LM01_L1TP_240061_19730313_20180427_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/240/061/LM01_L1TP_240061_19730313_20180427_01_T2/LM01_L1TP_240061_19730313_20180427_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM01/01/240/061/LM01_L1TP_240061_19730313_20180427_01_T2/LM01_L1TP_240061_19730313_20180427_01_T2_B7.TIF",
    },
}

# Mock data for landsat 2.
l2_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_2",
            "sensor_id": "MSS",
            "product_id": "LM02_L1TP_240061_19781016_20180421_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1978, 10, 16, 12, 28, 9, 899000),
            "mgrs_tile": None,
            "cloud_cover": 26.0,
            "wrs_path": 240,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LM02/01/240/061/LM02_L1TP_240061_19781016_20180421_01_T2",
        }
    ]
)

l2_expected_scene = {
    "spacecraft_id": "LANDSAT_2",
    "sensor_id": "MSS",
    "product_id": "LM02_L1TP_240061_19781016_20180421_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1978, 10, 16, 12, 28, 9, 899000),
    "mgrs_tile": None,
    "cloud_cover": 26.0,
    "wrs_path": 240,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LM02/01/240/061/LM02_L1TP_240061_19781016_20180421_01_T2",
    "bands": {
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/240/061/LM02_L1TP_240061_19781016_20180421_01_T2/LM02_L1TP_240061_19781016_20180421_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/240/061/LM02_L1TP_240061_19781016_20180421_01_T2/LM02_L1TP_240061_19781016_20180421_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/240/061/LM02_L1TP_240061_19781016_20180421_01_T2/LM02_L1TP_240061_19781016_20180421_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM02/01/240/061/LM02_L1TP_240061_19781016_20180421_01_T2/LM02_L1TP_240061_19781016_20180421_01_T2_B7.TIF",
    },
}

# Mock data for landsat 3.
l3_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_3",
            "sensor_id": "MSS",
            "product_id": "LM03_L1GS_080061_19780501_20180420_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1978, 5, 1, 21, 21, 14, 72000),
            "mgrs_tile": None,
            "cloud_cover": 83.0,
            "wrs_path": 80,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LM03/01/080/061/LM03_L1GS_080061_19780501_20180420_01_T2",
        }
    ]
)

l3_expected_scene = {
    "spacecraft_id": "LANDSAT_3",
    "sensor_id": "MSS",
    "product_id": "LM03_L1GS_080061_19780501_20180420_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1978, 5, 1, 21, 21, 14, 72000),
    "mgrs_tile": None,
    "cloud_cover": 83.0,
    "wrs_path": 80,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LM03/01/080/061/LM03_L1GS_080061_19780501_20180420_01_T2",
    "bands": {
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/080/061/LM03_L1GS_080061_19780501_20180420_01_T2/LM03_L1GS_080061_19780501_20180420_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/080/061/LM03_L1GS_080061_19780501_20180420_01_T2/LM03_L1GS_080061_19780501_20180420_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/080/061/LM03_L1GS_080061_19780501_20180420_01_T2/LM03_L1GS_080061_19780501_20180420_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LM03/01/080/061/LM03_L1GS_080061_19780501_20180420_01_T2/LM03_L1GS_080061_19780501_20180420_01_T2_B7.TIF",
    },
}

# Mock data for landsat 4.
l4_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_4",
            "sensor_id": "TM",
            "product_id": "LT04_L1GS_076061_19930316_20170119_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(1993, 3, 16, 21, 28, 24, 379038),
            "mgrs_tile": None,
            "cloud_cover": 78.0,
            "wrs_path": 76,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2",
        }
    ]
)

l4_expected_scene = {
    "spacecraft_id": "LANDSAT_4",
    "sensor_id": "TM",
    "product_id": "LT04_L1GS_076061_19930316_20170119_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(1993, 3, 16, 21, 28, 24, 379038),
    "mgrs_tile": None,
    "cloud_cover": 78.0,
    "wrs_path": 76,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT04/01/076/061/LT04_L1GS_076061_19930316_20170119_01_T2/LT04_L1GS_076061_19930316_20170119_01_T2_B7.TIF",
    },
}

# Mock data for landsat 5.
l5_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_5",
            "sensor_id": "TM",
            "product_id": "LT05_L1TP_223061_20111026_20161005_01_T1",
            "granule_id": None,
            "sensing_time": datetime.datetime(2011, 10, 26, 13, 11, 1, 160025),
            "mgrs_tile": None,
            "cloud_cover": 40.0,
            "wrs_path": 223,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1",
        }
    ]
)

l5_expected_scene = {
    "spacecraft_id": "LANDSAT_5",
    "sensor_id": "TM",
    "product_id": "LT05_L1TP_223061_20111026_20161005_01_T1",
    "granule_id": None,
    "sensing_time": datetime.datetime(2011, 10, 26, 13, 11, 1, 160025),
    "mgrs_tile": None,
    "cloud_cover": 40.0,
    "wrs_path": 223,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LT05/01/223/061/LT05_L1TP_223061_20111026_20161005_01_T1/LT05_L1TP_223061_20111026_20161005_01_T1_B7.TIF",
    },
}


# Mock data for landsat 7.
l7_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_7",
            "sensor_id": "ETM",
            "product_id": "LE07_L1GT_223061_20200128_20200223_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(2020, 1, 28, 13, 2, 37, 153212),
            "mgrs_tile": None,
            "cloud_cover": 59.0,
            "wrs_path": 223,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2",
        }
    ]
)

l7_expected_scene = {
    "spacecraft_id": "LANDSAT_7",
    "sensor_id": "ETM",
    "product_id": "LE07_L1GT_223061_20200128_20200223_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(2020, 1, 28, 13, 2, 37, 153212),
    "mgrs_tile": None,
    "cloud_cover": 59.0,
    "wrs_path": 223,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LE07/01/223/061/LE07_L1GT_223061_20200128_20200223_01_T2/LE07_L1GT_223061_20200128_20200223_01_T2_B8.TIF",
    },
}

# Mock data for landsat 8.
l8_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_8",
            "sensor_id": "OLI_TIRS",
            "product_id": "LC08_L1TP_224061_20210129_20210306_01_T2",
            "granule_id": None,
            "sensing_time": datetime.datetime(2021, 1, 29, 13, 29, 24, 756888),
            "mgrs_tile": None,
            "cloud_cover": 59.59,
            "wrs_path": 224,
            "wrs_row": 61,
            "base_url": "gs://gcp-public-data-landsat/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2",
        }
    ]
)

l8_expected_scene = {
    "spacecraft_id": "LANDSAT_8",
    "sensor_id": "OLI_TIRS",
    "product_id": "LC08_L1TP_224061_20210129_20210306_01_T2",
    "granule_id": None,
    "sensing_time": datetime.datetime(2021, 1, 29, 13, 29, 24, 756888),
    "mgrs_tile": None,
    "cloud_cover": 59.59,
    "wrs_path": 224,
    "wrs_row": 61,
    "base_url": "gs://gcp-public-data-landsat/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2",
    "bands": {
        "B1": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B1.TIF",
        "B2": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B2.TIF",
        "B3": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B3.TIF",
        "B4": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B4.TIF",
        "B5": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B5.TIF",
        "B6": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B6.TIF",
        "B7": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B7.TIF",
        "B8": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B8.TIF",
        "B9": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B9.TIF",
        "B10": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B10.TIF",
        "B11": "https://gcp-public-data-landsat.commondatastorage.googleapis.com/LC08/01/224/061/LC08_L1TP_224061_20210129_20210306_01_T2/LC08_L1TP_224061_20210129_20210306_01_T2_B11.TIF",
    },
}
