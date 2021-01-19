import json
import os
import unittest
from unittest import mock

import mock_functions
import numpy
from rasterio import Affine
from rasterio.io import MemoryFile

from pixels import algebra, core, utils
from tests.configs import gen_config, gen_configs

COORDS = json.load(
    open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "coords.json")
    )
)
GEOM = {"type": "Polygon", "coordinates": COORDS}
GEOM_MULTI = {"type": "MultiPolygon", "coordinates": [COORDS]}


@mock.patch("pixels.scihub.warp_from_s3", mock_functions.warp_from_s3)
@mock.patch("pixels.core.search.search", mock_functions.search)
class TestPixels(unittest.TestCase):
    @unittest.skip("Not fixed")
    def test_memory(self):
        config = gen_config({"mode": "latest_pixel"})
        config = utils.validate_configuration(config)
        for i in range(1000):
            if i % 50 == 0:
                print("here ---------- ", i)
            core.handler(config)

    def test_pixels(self):
        for config in gen_configs():
            config = utils.validate_configuration(config)
            core.handler(config)

    def test_timeseries(self):
        config = gen_config({"interval": "weeks", "interval_step": 1})
        config = utils.validate_configuration(config)
        for here_start, here_end in utils.timeseries_steps(
            config["start"], config["end"], config["interval"], config["interval_step"]
        ):
            # Update config with intermediate timestamps.
            config.update(
                {
                    "start": str(here_start.date()),
                    "end": str(here_end.date()),
                }
            )
            # Trigger async task.
            core.handler(config)

    def test_algebra(self):
        height = width = 512
        creation_args = {
            "driver": "GTiff",
            "dtype": "uint16",
            "nodata": 0,
            "count": 1,
            "crs": "epsg:4326",
            "transform": Affine(1, 0, 0, 0, -1, 0),
            "width": width,
            "height": height,
        }
        # Open memory destination file.
        memfile_b8 = MemoryFile()
        fake_data_b8 = (numpy.random.random((1, height, width)) * 1e3).astype("uint16")
        with memfile_b8.open(**creation_args) as rst:
            rst.write(fake_data_b8)

        memfile_b4 = MemoryFile()
        fake_data_b4 = (numpy.random.random((1, height, width)) * 1e3).astype("uint16")
        with memfile_b4.open(**creation_args) as rst:
            rst.write(fake_data_b4)
        # Evaluate formula.
        parser = algebra.FormulaParser()
        data = {"B08": memfile_b8, "B04": memfile_b4}
        result = parser.evaluate(data, "(B08 - B04) / (B08 + B04)").ravel()
        # Evaluate expected array.
        expected = (
            (fake_data_b8.astype("float64") - fake_data_b4.astype("float64"))
            / (fake_data_b8.astype("float64") + fake_data_b4.astype("float64"))
        ).ravel()
        # Arrays are equal.
        numpy.testing.assert_array_equal(result, expected)
        # Results are within expected range.
        self.assertFalse(numpy.any(result > 1.0))
        self.assertFalse(numpy.any(result < -1.0))

    def test_reproject_feature(self):
        feat = {
            "geometry": GEOM,
            "crs": "EPSG:3857",
        }
        result = utils.reproject_feature(feat, "EPSG:4326")
        self.assertEqual(result["crs"], "EPSG:4326")
        self.assertEqual(
            result["geometry"]["coordinates"][0][0],
            (-7.273839640000012, 41.22875735999998),
        )

    def test_geometry_to_wkt(self):
        result = utils.geometry_to_wkt(GEOM)
        self.assertIn("POLYGON((-809720.1248367296 5046142.10146797", result)
        result = utils.geometry_to_wkt(GEOM_MULTI)
        self.assertIn("MULTIPOLYGON(((-809720.1248367296 5046142.10146797", result)


if __name__ == "__main__":
    unittest.main()
