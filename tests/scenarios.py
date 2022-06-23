import datetime
from unittest.mock import MagicMock

sentinel_2_data_mock = MagicMock(
    return_value=[
        {
            "id": "S2A_29TNG_20170128_0_L2A",
            "collection_id": "sentinel-s2-l2a-cogs",
            "datetime": datetime.datetime(
                2017, 1, 28, 11, 33, 22, tzinfo=datetime.timezone.utc
            ),
            "properties": {
                "gsd": 10,
                "created": "2020-09-18T06:14:23.388Z",
                "updated": "2020-09-18T06:14:23.388Z",
                "datetime": "2017-01-28T11:33:22Z",
                "platform": "sentinel-2a",
                "proj:epsg": 32629,
                "instruments": ["msi"],
                "constellation": "sentinel-2",
                "eo:cloud_cover": 81.59,
                "view:off_nadir": 0,
                "sentinel:sequence": "0",
                "sentinel:utm_zone": 29,
                "sentinel:product_id": "S2A_MSIL2A_20170128T113321_N0001_R080_T29TNG_20190506T060629",
                "sentinel:grid_square": "NG",
                "sentinel:data_coverage": 88.44,
                "sentinel:latitude_band": "T",
                "sentinel:valid_cloud_cover": True,
            },
            "assets": {
                "AOT": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/AOT.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Aerosol Optical Thickness (AOT)",
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B01": {
                    "gsd": 60,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B01.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 1 (coastal)",
                    "eo:bands": [
                        {
                            "name": "B01",
                            "common_name": "coastal",
                            "center_wavelength": 0.4439,
                            "full_width_half_max": 0.027,
                        }
                    ],
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B02": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B02.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 2 (blue)",
                    "eo:bands": [
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B03": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B03.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 3 (green)",
                    "eo:bands": [
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B04": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B04.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 4 (red)",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B05": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B05.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 5",
                    "eo:bands": [
                        {
                            "name": "B05",
                            "center_wavelength": 0.7039,
                            "full_width_half_max": 0.019,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B06": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B06.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 6",
                    "eo:bands": [
                        {
                            "name": "B06",
                            "center_wavelength": 0.7402,
                            "full_width_half_max": 0.018,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B07": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B07.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 7",
                    "eo:bands": [
                        {
                            "name": "B07",
                            "center_wavelength": 0.7825,
                            "full_width_half_max": 0.028,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B08": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B08.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 8 (nir)",
                    "eo:bands": [
                        {
                            "name": "B08",
                            "common_name": "nir",
                            "center_wavelength": 0.8351,
                            "full_width_half_max": 0.145,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B09": {
                    "gsd": 60,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B09.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 9",
                    "eo:bands": [
                        {
                            "name": "B09",
                            "center_wavelength": 0.945,
                            "full_width_half_max": 0.026,
                        }
                    ],
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B11": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B11.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 11 (swir16)",
                    "eo:bands": [
                        {
                            "name": "B11",
                            "common_name": "swir16",
                            "center_wavelength": 1.6137,
                            "full_width_half_max": 0.143,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B12": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B12.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 12 (swir22)",
                    "eo:bands": [
                        {
                            "name": "B12",
                            "common_name": "swir22",
                            "center_wavelength": 2.22024,
                            "full_width_half_max": 0.242,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B8A": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/B8A.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 8A",
                    "eo:bands": [
                        {
                            "name": "B8A",
                            "center_wavelength": 0.8648,
                            "full_width_half_max": 0.033,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "SCL": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/SCL.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Scene Classification Map (SCL)",
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "WVP": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/WVP.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Water Vapour (WVP)",
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "info": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/29/T/NG/2017/1/28/0/tileInfo.json",
                    "type": "application/json",
                    "roles": ["metadata"],
                    "title": "Original JSON metadata",
                },
                "visual": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/TCI.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["overview"],
                    "title": "True color image",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        },
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        },
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        },
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "metadata": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/29/T/NG/2017/1/28/0/metadata.xml",
                    "type": "application/xml",
                    "roles": ["metadata"],
                    "title": "Original XML metadata",
                },
                "overview": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170128_0_L2A/L2A_PVI.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["overview"],
                    "title": "True color image",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        },
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        },
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        },
                    ],
                    "proj:shape": [343, 343],
                    "proj:transform": [320, 0, 499980, 0, -320, 4700040, 0, 0, 1],
                },
                "thumbnail": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l1c/tiles/29/T/NG/2017/1/28/0/preview.jpg",
                    "type": "image/png",
                    "roles": ["thumbnail"],
                    "title": "Thumbnail",
                },
            },
        },
        {
            "id": "S2A_29TNG_20170105_0_L2A",
            "collection_id": "sentinel-s2-l2a-cogs",
            "datetime": datetime.datetime(
                2017, 1, 5, 11, 27, 37, tzinfo=datetime.timezone.utc
            ),
            "properties": {
                "gsd": 10,
                "created": "2020-09-01T15:32:53.423Z",
                "updated": "2020-09-01T15:32:53.423Z",
                "datetime": "2017-01-05T11:27:37Z",
                "platform": "sentinel-2a",
                "proj:epsg": 32629,
                "instruments": ["msi"],
                "constellation": "sentinel-2",
                "eo:cloud_cover": 15.41,
                "view:off_nadir": 0,
                "sentinel:sequence": "0",
                "sentinel:utm_zone": 29,
                "sentinel:product_id": "S2A_MSIL2A_20170105T112442_N0001_R037_T29TNG_20190506T074729",
                "sentinel:grid_square": "NG",
                "sentinel:data_coverage": 96.2,
                "sentinel:latitude_band": "T",
                "sentinel:valid_cloud_cover": True,
            },
            "assets": {
                "AOT": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/AOT.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Aerosol Optical Thickness (AOT)",
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B01": {
                    "gsd": 60,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B01.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 1 (coastal)",
                    "eo:bands": [
                        {
                            "name": "B01",
                            "common_name": "coastal",
                            "center_wavelength": 0.4439,
                            "full_width_half_max": 0.027,
                        }
                    ],
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B02": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B02.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 2 (blue)",
                    "eo:bands": [
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B03": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B03.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 3 (green)",
                    "eo:bands": [
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B04": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B04.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 4 (red)",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B05": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B05.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 5",
                    "eo:bands": [
                        {
                            "name": "B05",
                            "center_wavelength": 0.7039,
                            "full_width_half_max": 0.019,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B06": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B06.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 6",
                    "eo:bands": [
                        {
                            "name": "B06",
                            "center_wavelength": 0.7402,
                            "full_width_half_max": 0.018,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B07": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B07.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 7",
                    "eo:bands": [
                        {
                            "name": "B07",
                            "center_wavelength": 0.7825,
                            "full_width_half_max": 0.028,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B08": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B08.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 8 (nir)",
                    "eo:bands": [
                        {
                            "name": "B08",
                            "common_name": "nir",
                            "center_wavelength": 0.8351,
                            "full_width_half_max": 0.145,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B09": {
                    "gsd": 60,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B09.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 9",
                    "eo:bands": [
                        {
                            "name": "B09",
                            "center_wavelength": 0.945,
                            "full_width_half_max": 0.026,
                        }
                    ],
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B11": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B11.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 11 (swir16)",
                    "eo:bands": [
                        {
                            "name": "B11",
                            "common_name": "swir16",
                            "center_wavelength": 1.6137,
                            "full_width_half_max": 0.143,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B12": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B12.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 12 (swir22)",
                    "eo:bands": [
                        {
                            "name": "B12",
                            "common_name": "swir22",
                            "center_wavelength": 2.22024,
                            "full_width_half_max": 0.242,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B8A": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/B8A.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 8A",
                    "eo:bands": [
                        {
                            "name": "B8A",
                            "center_wavelength": 0.8648,
                            "full_width_half_max": 0.033,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "SCL": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/SCL.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Scene Classification Map (SCL)",
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "WVP": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/WVP.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Water Vapour (WVP)",
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "info": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/29/T/NG/2017/1/5/0/tileInfo.json",
                    "type": "application/json",
                    "roles": ["metadata"],
                    "title": "Original JSON metadata",
                },
                "visual": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/TCI.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["overview"],
                    "title": "True color image",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        },
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        },
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        },
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "metadata": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/29/T/NG/2017/1/5/0/metadata.xml",
                    "type": "application/xml",
                    "roles": ["metadata"],
                    "title": "Original XML metadata",
                },
                "overview": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170105_0_L2A/L2A_PVI.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["overview"],
                    "title": "True color image",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        },
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        },
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        },
                    ],
                    "proj:shape": [343, 343],
                    "proj:transform": [320, 0, 499980, 0, -320, 4700040, 0, 0, 1],
                },
                "thumbnail": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l1c/tiles/29/T/NG/2017/1/5/0/preview.jpg",
                    "type": "image/png",
                    "roles": ["thumbnail"],
                    "title": "Thumbnail",
                },
            },
        },
        {
            "id": "S2A_29TNG_20170125_0_L2A",
            "collection_id": "sentinel-s2-l2a-cogs",
            "datetime": datetime.datetime(
                2017, 1, 25, 11, 23, 33, tzinfo=datetime.timezone.utc
            ),
            "properties": {
                "gsd": 10,
                "created": "2020-09-27T22:34:59.897Z",
                "updated": "2020-09-27T22:34:59.897Z",
                "datetime": "2017-01-25T11:23:33Z",
                "platform": "sentinel-2a",
                "proj:epsg": 32629,
                "instruments": ["msi"],
                "constellation": "sentinel-2",
                "data_coverage": 95.92,
                "eo:cloud_cover": 2.28,
                "view:off_nadir": 0,
                "sentinel:sequence": "0",
                "sentinel:utm_zone": 29,
                "sentinel:product_id": "S2A_MSIL2A_20170125T112331_N0001_R037_T29TNG_20190506T120522",
                "sentinel:grid_square": "NG",
                "sentinel:data_coverage": 95.92,
                "sentinel:latitude_band": "T",
                "sentinel:valid_cloud_cover": True,
            },
            "assets": {
                "AOT": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/AOT.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Aerosol Optical Thickness (AOT)",
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B01": {
                    "gsd": 60,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B01.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 1 (coastal)",
                    "eo:bands": [
                        {
                            "name": "B01",
                            "common_name": "coastal",
                            "center_wavelength": 0.4439,
                            "full_width_half_max": 0.027,
                        }
                    ],
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B02": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B02.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 2 (blue)",
                    "eo:bands": [
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B03": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B03.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 3 (green)",
                    "eo:bands": [
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B04": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B04.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 4 (red)",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B05": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B05.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 5",
                    "eo:bands": [
                        {
                            "name": "B05",
                            "center_wavelength": 0.7039,
                            "full_width_half_max": 0.019,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B06": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B06.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 6",
                    "eo:bands": [
                        {
                            "name": "B06",
                            "center_wavelength": 0.7402,
                            "full_width_half_max": 0.018,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B07": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B07.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 7",
                    "eo:bands": [
                        {
                            "name": "B07",
                            "center_wavelength": 0.7825,
                            "full_width_half_max": 0.028,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B08": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B08.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 8 (nir)",
                    "eo:bands": [
                        {
                            "name": "B08",
                            "common_name": "nir",
                            "center_wavelength": 0.8351,
                            "full_width_half_max": 0.145,
                        }
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "B09": {
                    "gsd": 60,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B09.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 9",
                    "eo:bands": [
                        {
                            "name": "B09",
                            "center_wavelength": 0.945,
                            "full_width_half_max": 0.026,
                        }
                    ],
                    "proj:shape": [1830, 1830],
                    "proj:transform": [60, 0, 499980, 0, -60, 4700040, 0, 0, 1],
                },
                "B11": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B11.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 11 (swir16)",
                    "eo:bands": [
                        {
                            "name": "B11",
                            "common_name": "swir16",
                            "center_wavelength": 1.6137,
                            "full_width_half_max": 0.143,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B12": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B12.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 12 (swir22)",
                    "eo:bands": [
                        {
                            "name": "B12",
                            "common_name": "swir22",
                            "center_wavelength": 2.22024,
                            "full_width_half_max": 0.242,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "B8A": {
                    "gsd": 20,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/B8A.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Band 8A",
                    "eo:bands": [
                        {
                            "name": "B8A",
                            "center_wavelength": 0.8648,
                            "full_width_half_max": 0.033,
                        }
                    ],
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "SCL": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/SCL.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Scene Classification Map (SCL)",
                    "proj:shape": [5490, 5490],
                    "proj:transform": [20, 0, 499980, 0, -20, 4700040, 0, 0, 1],
                },
                "WVP": {
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/WVP.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Water Vapour (WVP)",
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "info": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/29/T/NG/2017/1/25/0/tileInfo.json",
                    "type": "application/json",
                    "roles": ["metadata"],
                    "title": "Original JSON metadata",
                },
                "visual": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/TCI.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["overview"],
                    "title": "True color image",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        },
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        },
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        },
                    ],
                    "proj:shape": [10980, 10980],
                    "proj:transform": [10, 0, 499980, 0, -10, 4700040, 0, 0, 1],
                },
                "metadata": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/29/T/NG/2017/1/25/0/metadata.xml",
                    "type": "application/xml",
                    "roles": ["metadata"],
                    "title": "Original XML metadata",
                },
                "overview": {
                    "gsd": 10,
                    "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/29/T/NG/2017/1/S2A_29TNG_20170125_0_L2A/L2A_PVI.tif",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["overview"],
                    "title": "True color image",
                    "eo:bands": [
                        {
                            "name": "B04",
                            "common_name": "red",
                            "center_wavelength": 0.6645,
                            "full_width_half_max": 0.038,
                        },
                        {
                            "name": "B03",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                            "full_width_half_max": 0.045,
                        },
                        {
                            "name": "B02",
                            "common_name": "blue",
                            "center_wavelength": 0.4966,
                            "full_width_half_max": 0.098,
                        },
                    ],
                    "proj:shape": [343, 343],
                    "proj:transform": [320, 0, 499980, 0, -320, 4700040, 0, 0, 1],
                },
                "thumbnail": {
                    "href": "https://roda.sentinel-hub.com/sentinel-s2-l1c/tiles/29/T/NG/2017/1/25/0/preview.jpg",
                    "type": "image/png",
                    "roles": ["thumbnail"],
                    "title": "Thumbnail",
                },
            },
        },
    ]
)

landsat_data_mock = MagicMock(
    return_value=[
        {
            "id": "LC08_L2SP_204031_20170106_20200905_02_T1_SR",
            "collection_id": "landsat-c2l2-sr",
            "datetime": datetime.datetime(
                2017, 1, 6, 11, 13, 55, 122499, tzinfo=datetime.timezone.utc
            ),
            "properties": {
                "created": "2021-07-25T13:57:09.491Z",
                "updated": "2021-07-25T13:57:09.491Z",
                "datetime": "2017-01-06T11:13:55.122499Z",
                "platform": "LANDSAT_8",
                "proj:epsg": 32629,
                "proj:shape": [7831, 7711],
                "instruments": ["OLI", "TIRS"],
                "eo:cloud_cover": 15.03,
                "proj:transform": [30, 0, 468585, 0, -30, 4740615],
                "view:off_nadir": 0,
                "landsat:wrs_row": "031",
                "landsat:scene_id": "LC82040312017006LGN02",
                "landsat:wrs_path": "204",
                "landsat:wrs_type": "2",
                "view:sun_azimuth": 158.93560587,
                "landsat:correction": "L2SP",
                "view:sun_elevation": 22.92423803,
                "landsat:cloud_cover_land": 17.27,
                "landsat:collection_number": "02",
                "landsat:collection_category": "T1",
            },
            "assets": {
                "red": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B4.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B4.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Red Band (B4) Surface Reflectance",
                    "file:checksum": "1340171960de7079ebb7d123c36713515cabcd0446cbaa8dc69875a8bcaf88e01cfc9bd134cd0af6987de9ce8c6427d09a08d911c484365ff4d75283f052da919503",
                },
                "blue": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B2.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B2.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Blue Band (B2) Surface Reflectance",
                    "file:checksum": "1340b97fd1efea76fb1ead3ba6e179da73eb45fc36718e32812994ea0961b90daa04e553e6e246aa8050bba616576b60045efac1a1699c0e20d1a065700c471a4b08",
                },
                "green": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B3.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B3.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Green Band (B3) Surface Reflectance",
                    "file:checksum": "1340ab154eac9c0b4206214c48d32df68779f449ed8a4fec23bd54cb2583b03aa1d634708ba14004784107f1c56e13a7341cda1ec991b6cf644995ab313cb9922a90",
                },
                "index": {
                    "href": "https://landsatlook.usgs.gov/stac-browser/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1",
                    "type": "text/html",
                    "roles": ["metadata"],
                    "title": "HTML index page",
                },
                "nir08": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B5.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B5.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Near Infrared Band 0.8 (B5) Surface Reflectance",
                    "file:checksum": "13402c6daab12bafd4b450f9d7eeef9a5b10da3d03ace3611c55d63630958575e6f3d6989f0161b5c36c409a70727d5b76d58b2b0b3fe573c61169312deb824518d4",
                },
                "swir16": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B6.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B6.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Short-wave Infrared Band 1.6 (B6) Surface Reflectance",
                    "file:checksum": "1340dfd9be925a933b71c0e135d7b61b9f215c8794652b703c21d871475ee9569bc169673e925e9be9293706b12096460b4dc2d081afed8ee59b6bd5eb3df0627b93",
                },
                "swir22": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B7.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B7.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Short-wave Infrared Band 2.2 (B7) Surface Reflectance",
                    "file:checksum": "13409f319256d1ffaf330a98a506c0220628e0dfa50c582a14e5bae68d3eb453ec31e083cfab25dc9c331128445c4c25dc8a11036fdd466e7e192701bd4dd9e8753e",
                },
                "ANG.txt": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_ANG.txt",
                    "type": "text/plain",
                    "roles": ["metadata"],
                    "title": "Angle Coefficients File",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_ANG.txt",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Angle Coefficients File (ANG)",
                    "file:checksum": "134002e38ee39282aa05ece8e0c506538c1888e64d84cb4cc61f95480f882f0580b7596e8c7e0e3b64adbb15a7701371dcf9a49efcd51b15ca046696ad07d2c1f43f",
                },
                "MTL.txt": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_MTL.txt",
                    "type": "text/plain",
                    "roles": ["metadata"],
                    "title": "Product Metadata File",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_MTL.txt",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Product Metadata File (MTL)",
                    "file:checksum": "13401b7c970108f8451b7834862b5f3f4a83575095b51585e88fe2345b489fc349f73a8f1df7ac395e6764d77d0f545fb2a8dfbbdae1c97ccef5eebe65ebd556487b",
                },
                "MTL.xml": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_MTL.xml",
                    "type": "application/xml",
                    "roles": ["metadata"],
                    "title": "Product Metadata File (xml)",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_MTL.xml",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-1 Product Metadata File (xml)",
                    "file:checksum": "134045e49f35ae92ca981f8ef99b391eef4b5c1e007fd9a968339721e47e5209add18dafd636a79242acbd040d5ba31df5019e53383f2520bc95fbe4782f85e2286d",
                },
                "coastal": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B1.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_B1.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Coastal/Aerosol Band (B1) Surface Reflectance",
                    "file:checksum": "1340e619b571d8645679a4e80acd958315d34c8265f58535c18e617418a2f9115be4b0f52a17e7bf8d12f218da1ac9f950c7e81a5e5e3183edd6c1d6d7af96efad27",
                },
                "MTL.json": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_MTL.json",
                    "type": "application/json",
                    "roles": ["metadata"],
                    "title": "Product Metadata File (json)",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_MTL.json",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Product Metadata File (json)",
                    "file:checksum": "13402a1d1278b779770d417181694cedb734e995816ad94fc75cb5e9f0763da097970532ae1bbe6900e27818d2812f5caea42b134d7b4240770666336dfff21174f2",
                },
                "qa_pixel": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_QA_PIXEL.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["cloud", "cloud-shadow", "snow-ice", "water-mask"],
                    "title": "Pixel Quality Assessment Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_QA_PIXEL.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Pixel Quality Assessment Band Surface Reflectance",
                    "file:checksum": "13400a1300c196831041b0b2ba0a69f9fce5a2cd05405c8a8ae14def4ae353c8add4aa0e1e2132b64202689d4370f40ae328042db7868dfe38fe491e7ca9b239b28e",
                },
                "qa_radsat": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_QA_RADSAT.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["saturation"],
                    "title": "Radiometric Saturation Quality Assessment Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_QA_RADSAT.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Radiometric Saturation Quality Assessment Band Surface Reflectance",
                    "file:checksum": "13408c39074aa270f1797455859eaa8423966eb34aeb1d5120e9a0588528a860e02a09b5251396734dc8cf05077b6d97ab95ee68418749153609d7cd5ef4a7112926",
                },
                "thumbnail": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_thumb_small.jpeg",
                    "type": "image/jpeg",
                    "roles": ["thumbnail"],
                    "title": "Thumbnail image",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_thumb_small.jpeg",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "file:checksum": "134024c3536faee149c0f5d232b80f71f264430b9dc46a75e1559c9f5642175f05adbb1a65cdf4677517045ace8bb51d4b50763f421b0cfc6f99c5448225d7b8e6d6",
                },
                "qa_aerosol": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_QA_AEROSOL.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["metadata", "data-mask", "water-mask"],
                    "title": "Aerosol Quality Analysis Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_SR_QA_AEROSOL.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Aerosol Quality Analysis Band (ANG) Surface Reflectance",
                    "file:checksum": "1340e095d98400a38107278b25aa8a56de44cae58d8e178b5fd8fbff22e003a791df32e25ead1de5966bb842cd082aedd765ded02681f8689956a353ffcec7d377e5",
                },
                "reduced_resolution_browse": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_thumb_large.jpeg",
                    "type": "image/jpeg",
                    "roles": ["overview"],
                    "title": "Reduced resolution browse image",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2017/204/031/LC08_L2SP_204031_20170106_20200905_02_T1/LC08_L2SP_204031_20170106_20200905_02_T1_thumb_large.jpeg",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "file:checksum": "134057a121aaece516a7c36b8a3340431482c53c5fc07cf6d592bd0086c7e40cda8f6fd56219b366748157231bc6664a2ce10211f0adaed88e952c132ee88b357a77",
                },
            },
        },
        {
            "id": "LE07_L2SP_204031_20170130_20200901_02_T2_SR",
            "collection_id": "landsat-c2l2-sr",
            "datetime": datetime.datetime(
                2017, 1, 30, 11, 15, 43, 856138, tzinfo=datetime.timezone.utc
            ),
            "properties": {
                "created": "2021-07-24T11:40:43.404Z",
                "updated": "2021-07-24T11:40:43.404Z",
                "datetime": "2017-01-30T11:15:43.856138Z",
                "platform": "LANDSAT_7",
                "proj:epsg": 32629,
                "proj:shape": [7151, 8141],
                "instruments": ["ETM"],
                "eo:cloud_cover": 100,
                "proj:transform": [30, 0, 460785, 0, -30, 4731615],
                "view:off_nadir": 0,
                "landsat:wrs_row": "031",
                "landsat:scene_id": "LE72040312017030NSG00",
                "landsat:wrs_path": "204",
                "landsat:wrs_type": "2",
                "view:sun_azimuth": 155.8894353,
                "landsat:correction": "L2SP",
                "view:sun_elevation": 27.19500623,
                "landsat:cloud_cover_land": 100,
                "landsat:collection_number": "02",
                "landsat:collection_category": "T2",
            },
            "assets": {
                "red": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B3.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Red Band (B3)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B3",
                            "common_name": "red",
                            "center_wavelength": 0.65,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B3.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Red Band (B3) Surface Reflectance",
                    "file:checksum": "1340348b13ce0a6d76602565d0fd92b92aeaf22e611224efd3000b82d8b16cb268a0056073d873627c8192e76456156ccb18c3ef78e3f567e6557a600c3e2c2c06c3",
                },
                "blue": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B1.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Blue Band (B1)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B1",
                            "common_name": "blue",
                            "center_wavelength": 0.48,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B1.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Blue Band (B1) Surface Reflectance",
                    "file:checksum": "13400aca8e6563fa5a112c21f62742610210b71c2243a92c87de77d21ac58ad6d7c8db2adb78214c611072df85aca044864d663578f0c07f5dcd47eeb9aba070d2dc",
                },
                "green": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B2.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Green Band (B2)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B2",
                            "common_name": "green",
                            "center_wavelength": 0.56,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B2.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Green Band (B2) Surface Reflectance",
                    "file:checksum": "134052fafbf70cead034ade1121bed8da277efdae0a87939f4fee4f59de735898466bfad2e4f57ef5ed13899fe1a4b99e604c003e3979d83a555710edcbd5b6edab0",
                },
                "index": {
                    "href": "https://landsatlook.usgs.gov/stac-browser/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2",
                    "type": "text/html",
                    "roles": ["metadata"],
                    "title": "HTML index page",
                },
                "nir08": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B4.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data", "reflectance"],
                    "title": "Near Infrared Band 0.8 (B4)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B4",
                            "common_name": "nir08",
                            "center_wavelength": 0.86,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B4.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Near Infrared Band 0.8 (B4) Surface Reflectance",
                    "file:checksum": "13404ca33e1fb202fe8f6c37d6e87df40b89a7fa2fbe98f13246f767611dc10ded67016225dd0bc99c54c5c57e2d2e4b24645183309f30c08ef7e8ed20f2a921cbe6",
                },
                "swir16": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B5.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data", "reflectance"],
                    "title": "Short-wave Infrared Band 1.6 (B5)",
                    "eo:bands": [
                        {
                            "gsd": 30,
                            "name": "B5",
                            "common_name": "swir16",
                            "center_wavelength": 1.6,
                        }
                    ],
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B5.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Short-wave Infrared Band 1.6 (B6) Surface Reflectance",
                    "file:checksum": "13408fb1bf17381186c5f8929d51958846f1cb6d3e3e73bbcacd9b1339f22137f2db9c9b284f6ed84ac223f8f3ff4bc49cbf9359e8cadfbf55b42532a04822c24f85",
                },
                "swir22": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B7.TIF",
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
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_B7.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Short-wave Infrared Band 2.2 (B7) Surface Reflectance",
                    "file:checksum": "1340909995932b0135c4da2b44bd4c376d9fe5256d9f39a100db3b52e288d11b7653b022cd4b6b3bc22baaeccaf9ba96d7f7fbc850581c493ebcf4c2e42b8f9c3eff",
                },
                "ANG.txt": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_ANG.txt",
                    "type": "text/plain",
                    "roles": ["metadata"],
                    "title": "Angle Coefficients File",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_ANG.txt",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Angle Coefficients File (ANG)",
                    "file:checksum": "1340cd83bce0b4978a88833f8b10a9af636a8dd1e6eaaa410b080ac0391467da1803406c4b0e20dbbd3d7a30180c399ce4f51e64b411a9cbda58fb564e5f2df14826",
                },
                "MTL.txt": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_MTL.txt",
                    "type": "text/plain",
                    "roles": ["metadata"],
                    "title": "Product Metadata File",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_MTL.txt",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Product Metadata File (MTL)",
                    "file:checksum": "1340ca47f687340540dfaa21ee4fa820b81d4c6640b2b25a33ae77cc42dd11bc3e06d7d1a181d257a0270f067bc2c13ea7b204b9804890c1eebc4c3d931cd222125f",
                },
                "MTL.xml": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_MTL.xml",
                    "type": "application/xml",
                    "roles": ["metadata"],
                    "title": "Product Metadata File (xml)",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_MTL.xml",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-1 Product Metadata File (xml)",
                    "file:checksum": "13401d08fb4ac38585bb356d96351b3db8bad1b515fbd5a61347a2f6bba74dd2cc1b5ede55304b64461e44162217b88d4c90c8511eb8a5e55ed3455edce547387a7d",
                },
                "MTL.json": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_MTL.json",
                    "type": "application/json",
                    "roles": ["metadata"],
                    "title": "Product Metadata File (json)",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_MTL.json",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Product Metadata File (json)",
                    "file:checksum": "13406cae6575ebbcc28787e47a18019f0dce48e4380fedcf4f0a6675b6d35a6cacd5ac6b089a41917a8add31933c8c238633a48f5fd3663c4507b45fadc7ea91f9b0",
                },
                "cloud_qa": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_CLOUD_QA.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": [
                        "metadata",
                        "cloud",
                        "cloud-shadow",
                        "snow-ice",
                        "water-mask",
                    ],
                    "title": "Cloud Quality Analysis Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_CLOUD_QA.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Cloud Quality Opacity Band Surface Reflectance",
                    "file:checksum": "1340b97c2e96ad66782325270ea53061e236f2768904ead212523fc93473dad4a7d2c7ceb9477e8aa05860b7e184cf23fb758da148ba1d2518374fa035b3fa061f55",
                },
                "qa_pixel": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_QA_PIXEL.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["cloud", "cloud-shadow", "snow-ice", "water-mask"],
                    "title": "Pixel Quality Assessment Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_QA_PIXEL.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Pixel Quality Assessment Band Surface Reflectance",
                    "file:checksum": "134060a6cc7bc7c15d2e541328ee61a755396924cf415566e6b2ff8fe2b3027e5c0088181ab212fffdf3b8d790770b4eb94d6fc542110be478fba575fb8c9188cee7",
                },
                "qa_radsat": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_QA_RADSAT.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["saturation"],
                    "title": "Radiometric Saturation Quality Assessment Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_QA_RADSAT.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Radiometric Saturation Quality Assessment Band Surface Reflectance",
                    "file:checksum": "13403c58791f514b3482c528ada0cc727f06904d685c286d3bfb05401364b6015954da357bd79e979aabc275768b6b8e728040a8d4084a30c0c0ea26a1ba26f613eb",
                },
                "thumbnail": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_thumb_small.jpeg",
                    "type": "image/jpeg",
                    "roles": ["thumbnail"],
                    "title": "Thumbnail image",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_thumb_small.jpeg",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "file:checksum": "134029cf86f4a4acfc05d3e884c32f29db3b6f33bc3ec1635f0c2ef8b20d199dceff5b4045a93bb82b8f128a257ff67151e7db8b1b70698fef45af1b747cce96d719",
                },
                "atmos_opacity": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_ATMOS_OPACITY.TIF",
                    "type": "image/vnd.stac.geotiff; cloud-optimized=true",
                    "roles": ["data"],
                    "title": "Atmospheric Opacity Band",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_SR_ATMOS_OPACITY.TIF",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "description": "Collection 2 Level-2 Atmospheric Opacity Band Surface Reflectance",
                    "file:checksum": "134017d52b714956e8beda45ebe1373d6cc472c28a330a9da3e0028817b44cfea40c21f18941389a20cc92fffe6d9526a2d9442302896ac252a11a4be78ac64069ea",
                },
                "reduced_resolution_browse": {
                    "href": "https://landsatlook.usgs.gov/data/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_thumb_large.jpeg",
                    "type": "image/jpeg",
                    "roles": ["overview"],
                    "title": "Reduced resolution browse image",
                    "alternate": {
                        "s3": {
                            "href": "s3://usgs-landsat/collection02/level-2/standard/etm/2017/204/031/LE07_L2SP_204031_20170130_20200901_02_T2/LE07_L2SP_204031_20170130_20200901_02_T2_thumb_large.jpeg",
                            "storage:platform": "AWS",
                            "storage:requester_pays": True,
                        }
                    },
                    "file:checksum": "1340052d5770e15c0f79064799223a75bf2cb74cfa9c695616b1d4dac37a4a38e73f09f7d88a2307056337224b193b5cfd049b015c9f9ef4c82c76527ceb9786a4a3",
                },
            },
        },
    ]
)

empty_data_mock = MagicMock(return_value=[])

sample_geojson = {
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

product_info_mock = MagicMock(
    return_value={"Body": open("tests/data/productInfo.json")}
)
