import unittest

from pixels.combinations import get_index_bands


class CombinationsTest(unittest.TestCase):
    # RGB
    def test_get_rgb_s2(self):
        bands_names = get_index_bands("rgb", "SENTINEL_2")
        expected = {"red": "B04", "green": "B03", "blue": "B02"}
        self.assertEqual(expected, bands_names)

    def test_get_rgb_l8(self):
        bands_names = get_index_bands("rgb", "LANDSAT_8")
        expected = {"red": "B4", "green": "B3", "blue": "B2"}
        self.assertEqual(expected, bands_names)

    def test_get_rgb_l7(self):
        bands_names = get_index_bands("rgb", "LANDSAT_7")
        expected = {"red": "B3", "green": "B2", "blue": "B1"}
        self.assertEqual(expected, bands_names)

    def test_get_rgb_l5(self):
        bands_names = get_index_bands("rgb", "LANDSAT_5")
        expected = {"red": "B3", "green": "B2", "blue": "B1"}
        self.assertEqual(expected, bands_names)

    # Test ValueError
    def test_get_rgb_l3(self):
        self.assertRaises(ValueError, get_index_bands, "rgb", "LANDSAT_3")

    # NDVI
    def test_get_ndvi_s2(self):
        bands_names = get_index_bands("ndvi", "SENTINEL_2")
        expected = {"nir1": "B08", "red": "B04"}
        self.assertEqual(expected, bands_names)

    def test_get_ndvi_l8(self):
        bands_names = get_index_bands("ndvi", "LANDSAT_8")
        expected = {"nir1": "B5", "red": "B4"}
        self.assertEqual(expected, bands_names)

    def test_get_ndvi_l7(self):
        bands_names = get_index_bands("ndvi", "LANDSAT_7")
        expected = {"nir1": "B4", "red": "B3"}
        self.assertEqual(expected, bands_names)

    def test_get_ndvi_l5(self):
        bands_names = get_index_bands("ndvi", "LANDSAT_5")
        expected = {"nir1": "B4", "red": "B3"}
        self.assertEqual(expected, bands_names)

    def test_get_ndvi_l1(self):
        bands_names = get_index_bands("ndvi", "LANDSAT_1")
        expected = {"nir1": "B6", "red": "B5"}
        self.assertEqual(expected, bands_names)
