import datetime
import tempfile
import unittest

import numpy
import rasterio

from pixels.utils import timeseries_steps, write_raster


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
                self.assertEqual(src.tags(ns="tesselo").get("date"), "2021-01-01")
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
