import datetime
import tempfile
import unittest

import numpy
import rasterio

from pixels.utils import (
    cog_to_jp2_bucket,
    compute_transform,
    compute_wgs83_bbox,
    is_sentinel_cog_bucket,
    timeseries_steps,
    write_raster,
)


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
        self.data = numpy.arange(size ** 2, dtype="uint16").reshape((1, size, size))
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
