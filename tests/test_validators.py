import unittest

from pixels.validators import PixelsConfigValidator
from tests.scenarios import sample_geojson


def minimal_valid_config():
    return {
        "start": "2018-01-01",
        "platforms": "SENTINEL_2",
        "level": "L2A",
        "bands": ["B02,B03,B04,B08,B11,B12"],
        "geojson": sample_geojson.copy(),
    }


def complete_valid_config():
    config = minimal_valid_config()

    config.update(
        {
            "dynamic_dates_step": 2,
            "end": "2018-01-31",
            "interval": "all",
            "interval_step": 1,
            "scale": 10,
            "clip": True,
            "maxcloud": 20,
            "pool_size": 0,
            "limit": 100,
            "mode": "latest_pixel",
            "dynamic_dates_interval": "months",
        }
    )
    return config


class TestValidators(unittest.TestCase):
    def test_empty_config(self):
        with self.assertRaises(ValueError):
            PixelsConfigValidator()

    def test_minimal_valid_config(self):
        PixelsConfigValidator(**minimal_valid_config())

    def test_complete_valid_config(self):
        PixelsConfigValidator(**complete_valid_config())

    def test_invalid_platform(self):
        config = minimal_valid_config()
        config["platforms"] = ["SENTINEL_42"]
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_multiple_platforms(self):
        config = complete_valid_config()
        config["platforms"] = ["SENTINEL_2", "LANDSAT_8"]
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_level(self):
        config = minimal_valid_config()
        config["level"] = "L1F"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_bad_landsat_level(self):
        config = complete_valid_config()
        config["platforms"] = "LANDSAT_8"
        config["level"] = "L1C"
        with self.assertRaisesRegex(ValueError, "Level L1C is only for Sentinel-2"):
            PixelsConfigValidator(**config)

    def test_bad_sentinel_level(self):
        config = complete_valid_config()
        config["platforms"] = "SENTINEL_2"
        config["level"] = "LQUACK"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_landsad_level_in_sentinel_level(self):
        config = complete_valid_config()
        config["platforms"] = "SENTINEL_2"
        config["level"] = "L2"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_mismatch_bands(self):
        config = minimal_valid_config()
        config["bands"] = ["SCL"]
        config["level"] = "L1C"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_bands(self):
        config = minimal_valid_config()
        config["bands"] = 42
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_geojson(self):
        config = minimal_valid_config()
        config["geojson"] = {"type": "Point"}
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_geojson_crs(self):
        config = minimal_valid_config()
        config["geojson"]["crs"] = {"say": "haha!"}
        with self.assertRaisesRegex(ValueError, "crs dictionary is not valid"):
            PixelsConfigValidator(**config)

    def test_invalid_dynamic_dates_step(self):
        config = complete_valid_config()
        config["dynamic_dates_step"] = 0
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_dynamic_dates_interval(self):
        config = complete_valid_config()
        config["dynamic_dates_interval"] = "years"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_start_date(self):
        config = complete_valid_config()
        config["start"] = "2018-01-32"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_no_start_date_or_dynamic_interval(self):
        config = complete_valid_config()
        config["start"] = None
        config["dynamic_dates_interval"] = None
        with self.assertRaisesRegex(
            ValueError, "Start date is required for non dynamic dates"
        ):
            PixelsConfigValidator(**config)

    def test_invalid_end_date(self):
        config = complete_valid_config()
        config["end"] = "2018-41-01"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_interval(self):
        config = complete_valid_config()
        config["interval"] = "years"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_interval_step(self):
        config = complete_valid_config()
        config["interval_step"] = 0
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_scale(self):
        config = complete_valid_config()
        config["scale"] = -1
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_invalid_mode(self):
        config = complete_valid_config()
        config["mode"] = "invalid"
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)

    def test_mode_all(self):
        config = complete_valid_config()
        config["mode"] = "all"
        PixelsConfigValidator(**config)

    def test_extra_field_not_allowed(self):
        config = complete_valid_config()
        config["invalid"] = True
        with self.assertRaises(ValueError):
            PixelsConfigValidator(**config)
