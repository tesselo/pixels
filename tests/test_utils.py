import datetime
import tempfile
import unittest
from unittest.mock import patch

import numpy
import rasterio

from pixels.utils import (
    cog_to_jp2_bucket,
    compute_transform,
    compute_wgs83_bbox,
    is_sentinel_cog_bucket,
    is_sentinel_jp2_bucket,
    jp2_to_gcs_bucket,
    timeseries_steps,
    unwrap_arguments,
    write_raster,
)
from tests.scenarios import product_info_mock


class TestUtils(unittest.TestCase):
    def setUp(self):
        # Create temp raster.
        self.raster = tempfile.NamedTemporaryFile(suffix=".tif")
        scale = 10
        origin_x = -1028560.0
        origin_y = 4689560.0
        skew = 0
        size = 256
        self.creation_args = {
            "width": size,
            "height": size,
            "driver": "GTiff",
            "count": 1,
            "dtype": "uint16",
            "crs": "EPSG:3857",
            "nodata": 0,
            "transform": rasterio.Affine(scale, skew, origin_x, skew, -scale, origin_y),
        }
        self.data = numpy.arange(size**2, dtype="uint16").reshape((1, size, size))
        with rasterio.open(self.raster.name, "w", **self.creation_args) as dst:
            dst.write(self.data)
        self.geojson = {
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
                                [-1020256.0, 4680156.0],
                                [-1020256.0, 4680000.0],
                                [-1020000.0, 4680000.0],
                                [-1020000.0, 4680156.0],
                                [-1020256.0, 4680156.0],
                            ]
                        ],
                    },
                },
            ],
        }

    def test_write_raster(self):
        # Create file based case.
        dst = tempfile.NamedTemporaryFile(suffix=".tif")
        write_raster(
            self.data,
            self.creation_args,
            out_path=dst.name,
            driver="GTiff",
            dtype="uint16",
            overviews=True,
            tags={"date": "2021-01-01"},
        )
        # Create in-memory case.
        memrst = write_raster(
            self.data,
            self.creation_args,
            out_path=None,
            driver="GTiff",
            dtype="uint16",
            overviews=True,
            tags={"date": "2021-01-01"},
        )
        # Check content.
        for input in [dst.name, memrst]:
            with rasterio.open(input, "r") as src:
                # The array was written correctly.
                numpy.testing.assert_array_equal(
                    src.read(),
                    self.data,
                )
                # Tags were set.
                self.assertEqual(src.tags().get("date"), "2021-01-01")
                # Overviews were built.
                self.assertEqual(src.overviews(1), [2, 4, 8, 16, 32, 64])
                # Raster has internal tiling.
                self.assertTrue(src.is_tiled)

    def test_timeseries_steps(self):
        expected = [
            (datetime.date(2021, 1, 1), datetime.date(2021, 1, 14)),
            (datetime.date(2021, 1, 15), datetime.date(2021, 1, 28)),
        ]
        result = list(timeseries_steps("2021-01-01", "2021-02-01", "weeks", 2))
        self.assertEqual(result, expected)

    def test_compute_transform(self):
        transform, width, height = compute_transform(self.geojson, 1)
        self.assertEqual(height, 156)
        self.assertEqual(width, 256)
        self.assertEqual(
            list(transform),
            [1.0, 0.0, -1020256.0, 0.0, -1.0, 4680156.0, 0.0, 0.0, 1.0],
        )

    def test_compute_transform_tolerance_floor(self):
        self.geojson["features"][0]["geometry"]["coordinates"] = [
            [
                [-1020250.00001, 4680150.000001],
                [-1020250.00001, 4680000.0],
                [-1020000.0, 4680000.0],
                [-1020000.0, 4680150.000001],
                [-1020250.00001, 4680150.000001],
            ]
        ]
        transform, width, height = compute_transform(self.geojson, 10)
        self.assertEqual(height, 15)
        self.assertEqual(width, 25)

    def test_compute_transform_tolerance_ceil(self):
        self.geojson["features"][0]["geometry"]["coordinates"] = [
            [
                [-1020250.01, 4680150.01],
                [-1020250.01, 4680000.0],
                [-1020000.0, 4680000.0],
                [-1020000.0, 4680150.01],
                [-1020250.01, 4680150.000001],
            ]
        ]
        transform, width, height = compute_transform(self.geojson, 10)
        self.assertEqual(height, 16)
        self.assertEqual(width, 26)

    def test_compute_wgs84_bbox(self):
        # Geojson feature case.
        bbox = compute_wgs83_bbox(self.geojson)
        expected = [
            [
                [-9.165115585146461, 38.70848390053471],
                [-9.165115585146461, 38.70957743561777],
                [-9.162815898019115, 38.70957743561777],
                [-9.162815898019115, 38.70848390053471],
                [-9.165115585146461, 38.70848390053471],
            ]
        ]
        self.assertEqual(bbox["type"], "Polygon")
        numpy.testing.assert_almost_equal(bbox["coordinates"], expected)
        # BBox case.
        bbox = compute_wgs83_bbox(self.geojson, return_bbox=True)
        expected = (
            -9.165115585146461,
            38.70848390053471,
            -9.162815898019115,
            38.70957743561777,
        )
        numpy.testing.assert_almost_equal(bbox, expected)

    def test_is_sentinel_cog_bucket(self):
        self.assertFalse(
            is_sentinel_cog_bucket(
                "s3://sentinel-s2-l2a/tiles/29/S/ND/2021/12/15/0/R10m/B02.jp2"
            )
        )

        self.assertTrue(
            is_sentinel_cog_bucket(
                "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
                "sentinel-s2-l2a-cogs/29/S/ND/2021/12/S2B_29SND_20211215_0_L2A/B06.tif"
            )
        )

    def test_cog_to_jp2_bucket(self):
        expected = "s3://sentinel-s2-l2a/tiles/29/S/ND/2021/12/15/0/R20m/B06.jp2"
        transformed = cog_to_jp2_bucket(
            "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
            "sentinel-s2-l2a-cogs/29/S/ND/2021/12/S2B_29SND_20211215_0_L2A/B06.tif"
        )

        self.assertEqual(expected, transformed)

        expected = "s3://sentinel-s2-l2a/tiles/31/N/HA/2019/10/7/0/R20m/B11.jp2"
        transformed = cog_to_jp2_bucket(
            "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
            "sentinel-s2-l2a-cogs/31/N/HA/2019/10/S2B_31NHA_20191007_0_L2A/B11.tif"
        )

        self.assertEqual(expected, transformed)

    def test_unwrap_arguments(self):
        expected = [(1, "hu", "ha"), (2, "hu", "ha"), (3, "hu", "ha")]
        result = list(unwrap_arguments([(1, 2, 3)], ["hu", "ha"]))
        self.assertEqual(expected, result)

        expected = [(1, 4, "hu", "ha"), (2, 5, "hu", "ha"), (3, 6, "hu", "ha")]
        result = list(unwrap_arguments([(1, 2, 3), (4, 5, 6)], ["hu", "ha"]))
        self.assertEqual(expected, result)

        expected = [(1, 4, "hu", "ha"), (2, 5, "hu", "ha"), (3, 6, "hu", "ha")]
        result = list(unwrap_arguments([[1, 2, 3], [4, 5, 6]], ["hu", "ha"]))
        self.assertEqual(expected, result)

    def test_is_sentinel_jp2_bucket(self):
        self.assertFalse(
            is_sentinel_jp2_bucket(
                "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
                "sentinel-s2-l2a-cogs/29/S/ND/2021/12/S2B_29SND_20211215_0_L2A/B06.tif"
            )
        )

        self.assertTrue(
            is_sentinel_jp2_bucket(
                "s3://sentinel-s2-l2a/tiles/29/S/ND/2021/12/15/0/R10m/B02.jp2"
            )
        )

    @patch("pixels.utils.open_file_from_s3", product_info_mock)
    def test_jp2_to_gcs_bucket(self):
        self.assertEqual(
            jp2_to_gcs_bucket(
                "s3://sentinel-s2-l2a/tiles/2/D/MG/2019/3/1/0/R10m/B02.jp2"
            ),
            "https://storage.googleapis.com/gcp-public-data-sentinel-2/L2/tiles/02/D/MG/S2B_MSIL2A_20190301T202209_N0211_R042_T02DMG_20190301T220107.SAFE/GRANULE/L2A_T02DMG_A010364_20190301T202210/IMG_DATA/R10m/T02DMG_20190301T202209_B02_10m.jp2",
        )
