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


l8_l2_data_mock = MagicMock(
    return_value=[
        {
            "spacecraft_id": "LANDSAT_8",
            "sensor_id": '["OLI", "TIRS"]',
            "product_id": "LC08_L2SP_168075_20150222_20200909_02_T1_SR",
            "sensing_time": datetime.datetime(2015, 2, 22, 7, 48, 34, 713438),
            "cloud_cover": 43.28,
            "wrs_path": "168",
            "wrs_row": "075",
            "base_url": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_stac.json",
            "links": {
                "red": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B4.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Red Band (B4)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B4",
                            "common_name": "red",
                            "center_wavelength": 0.65,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B4.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Red Band (B4) Surface Reflectance",
                    "file:checksum": "1340bb0109bbfee3a267edd3e038a3433385d8e636ba593a7833eee22f9a84f27ca0f2de51bc7be00f50e4c535bf539ffd2bad38c294a6a90216732c5f315879916e",
                },
                "blue": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B2.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Blue Band (B2)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B2",
                            "common_name": "blue",
                            "center_wavelength": 0.48,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B2.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Blue Band (B2) Surface Reflectance",
                    "file:checksum": "1340236b2e1844d966a0b1033d84c20c5bc9cf11639ec69f0c5c2821c74a36c7eeb47f6e39219ebf6ad559939f1b75850dfff5ae685ff111102a3cdcc948bd3c62e2",
                },
                "green": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B3.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Green Band (B3)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B3",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B3.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Green Band (B3) Surface Reflectance",
                    "file:checksum": "13402208bb5b07cb8d526f87f09244477cba0826ffd717882e7c330ff7465b066befa3bf34f430d1ac46fd49d783bb5609ef2cacd20de28989be83e16cdd901218ff",
                },
                "index": {
                    "href": "https://landsatlook.usgs.gov/stac-browser/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1",
                    "type": "text/html",
                    "roles": ["metadata"],
                    "title": "HTML index page",
                },
                "nir08": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B5.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data", "reflectance"],
                    "title": "Near Infrared Band 0.8 (B5)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B5",
                            "common_name": "nir08",
                            "center_wavelength": 0.86,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B5.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Near Infrared Band 0.8 (B5) Surface Reflectance",
                    "file:checksum": "134026c23a82dd9edb79aa34bfcd83e527adb0e0ddcf31c12ca574cd52c344bb292306603f5823cd9fbbda3eb9ddea1a30d07bcf9f42b2a47ed93dd3895f82eda5ec",
                },
                "swir16": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B6.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data", "reflectance"],
                    "title": "Short-wave Infrared Band 1.6 (B6)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B6",
                            "common_name": "swir16",
                            "center_wavelength": 1.6,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B6.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Short-wave Infrared Band 1.6 (B6) Surface Reflectance",
                    "file:checksum": "1340c78755b2033dea2bcd6a5a09db85b5553fe5045d76fd741a116ab30f73704a6f3378b378efa8c77dd54a662e6219cfae4f5b67d7eb0197af9e8d6645fab6ad10",
                },
                "swir22": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B7.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data", "reflectance"],
                    "title": "Short-wave Infrared Band 2.2 (B7)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B7",
                            "common_name": "swir22",
                            "center_wavelength": 2.2,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B7.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Short-wave Infrared Band 2.2 (B7) Surface Reflectance",
                    "file:checksum": "1340899f2371cd63517822d7d507eb18f452fd55e36383a442b50fbe88f65b74ae9a3cf7fc01ada617486b970d99d37f9487b1690c6271a66b150279de8c2b8ae745",
                },
                "ANG.txt": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_ANG.txt",
                    "type": "text/plain",
                    "roles": ["metadata"],
                    "title": "Angle Coefficients File",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_ANG.txt",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Angle Coefficients File (ANG)",
                    "file:checksum": "13406d61c5a377327c807ebe6e826f4c8edb53c42215efb63d72c6cfc214c0e767f1bcb5e4f2e8daa15a78741c5b48500333f1b5e931badda68e4faa8dc97f396774",
                },
                "MTL.txt": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_MTL.txt",
                    "type": "text/plain",
                    "roles": ["metadata"],
                    "title": "Product Metadata File",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_MTL.txt",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Product Metadata File (MTL)",
                    "file:checksum": "13404e4e3b5a5596cfe0e7582ec87019e31abcd228006749242cc5a4f1f87eaa8da482327bd9f6a67c576086ba03343945646f9a122b515b92e47f44aad952564edf",
                },
                "MTL.xml": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_MTL.xml",
                    "type": "application/xml",
                    "roles": ["metadata"],
                    "title": "Product Metadata File (xml)",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_MTL.xml",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-1 Product Metadata File (xml)",
                    "file:checksum": "13406bf9c1d68494a186316b6f828e684878f7706e1a2e8d5ea15c1ce30210cb75f9e0f1ff1b2030913450fc519797d5c58715b2332942081fa5a2ed904a58daa445",
                },
                "coastal": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B1.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Coastal/Aerosol Band (B1)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B1",
                            "common_name": "coastal",
                            "center_wavelength": 0.44,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B1.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Coastal/Aerosol Band (B1) Surface Reflectance",
                    "file:checksum": "1340c456557616ca467af090743e8a120f504909bfd1131d15e17cc0561808957f659b7591467697283c6d093cab926b2ad92b6a074c51a1aedd7fd9b5cd7e7c4e82",
                },
                "MTL.json": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_MTL.json",
                    "type": "application/json",
                    "roles": ["metadata"],
                    "title": "Product Metadata File (json)",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_MTL.json",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Product Metadata File (json)",
                    "file:checksum": "1340ce06bf0b60bad650869141f35e80587dc141b472cc23ad1ee4182323357e48a482049de1c35e6f02997d552ce1d38639a4a653c0c9cd8ee3ff1b0ad8fa591ed6",
                },
                "qa_pixel": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_QA_PIXEL.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["cloud", "cloud-shadow", "snow-ice", "water-mask"],
                    "title": "Pixel Quality Assessment Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_QA_PIXEL.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Pixel Quality Assessment Band Surface Reflectance",
                    "file:checksum": "1340cc76f48636e56621df51112044c0c3b538c7ee878b956920fc802e28f2978143051b18384ddd0b80c4895acf56aeb4cfe7e130353f8da7be359e8c7176682c36",
                },
                "qa_radsat": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_QA_RADSAT.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["saturation"],
                    "title": "Radiometric Saturation Quality Assessment Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_QA_RADSAT.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Radiometric Saturation Quality Assessment Band Surface Reflectance",
                    "file:checksum": "1340bfc8dae2822ad1291b92f06d445db689492660dfa17305f11d5bc8bfec78169f751ea7887f6f83b148d329018225a4d1e8f9ea6869d4b8a7ffed406f275a445f",
                },
                "thumbnail": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_thumb_small.jpeg",
                    "type": "image/jpeg",
                    "roles": ["thumbnail"],
                    "title": "Thumbnail image",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_thumb_small.jpeg",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "file:checksum": "1340413198a45ea1c1360f95cbef9e8fd4b73cb6623909eea22412a572e0d8297d9613d79c14dcd1716435add750bf1d4fcb32bb03799eac5fc1ac1f792a21cd8113",
                },
                "qa_aerosol": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_QA_AEROSOL.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["metadata", "data-mask", "water-mask"],
                    "title": "Aerosol Quality Analysis Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_QA_AEROSOL.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Aerosol Quality Analysis Band (ANG) Surface Reflectance",
                    "file:checksum": "134078578f7cb60183ff695b338d9fd1773b7cc0f36035b0e70ea6170bca3cfec6c78d9fef9560eb7ae2d0e155b7263fb9f0b07eb9449a028d9e66e060bb01dca6e2",
                },
                "reduced_resolution_browse": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_thumb_large.jpeg",
                    "type": "image/jpeg",
                    "roles": ["overview"],
                    "title": "Reduced resolution browse image",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_thumb_large.jpeg",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "file:checksum": "1340d63dd34c6c5bf50083983e4e857a06a7f646c15c35db47759fb82d19c4d45f2c1d7a7453bbf79b81fea3993f94c2ea35b49df6709a05a4ee7d5e4738abfa3f7a",
                },
            },
        }
    ]
)


l8_l2_expected_scene = {
    "spacecraft_id": "LANDSAT_8",
    "sensor_id": '["OLI", "TIRS"]',
    "product_id": "LC08_L2SP_168075_20150222_20200909_02_T1_SR",
    "sensing_time": datetime.datetime(2015, 2, 22, 7, 48, 34, 713438),
    "cloud_cover": 43.28,
    "wrs_path": "168",
    "wrs_row": "075",
    "base_url": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_stac.json",
    "bands": {
        "B4": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B4.TIF",
        "B2": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B2.TIF",
        "B3": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B3.TIF",
        "B5": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B5.TIF",
        "B6": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B6.TIF",
        "B7": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B7.TIF",
        "B1": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_SR_B1.TIF",
        "QA_PIXEL": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_QA_PIXEL.TIF",
        "QA_SAT": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2015/168/075/LC08_L2SP_168075_20150222_20200909_02_T1/LC08_L2SP_168075_20150222_20200909_02_T1_QA_RADSAT.TIF",
    },
}
