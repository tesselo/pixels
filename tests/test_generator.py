import unittest

import numpy as np

from pixels.stac_generator.generator import DataGenerator
from tests import test_arrays


class TestGenerator(unittest.TestCase):
    def setUp(self):
        self.catalog_dict_path = "data/catalogs_dict.json"

    def test_simple_3D_case(self):
        gen_args = {
            "path_collection_catalog": self.catalog_dict_path,
            "split": 1,
            "train": True,
            "width": 3,
            "height": 3,
            "timesteps": 3,
            "num_bands": 4,
            "batch_number": 1,
            "mode": "3D_Model",
        }

        dtgen = DataGenerator(**gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_arrays.X_Simple3DCase)
        np.testing.assert_array_equal(y, test_arrays.Y_Simple3DCase)

    def test_simple_pixel_case(self):
        gen_args = {
            "path_collection_catalog": self.catalog_dict_path,
            "split": 1,
            "train": True,
            "timesteps": 3,
            "num_bands": 4,
            "batch_number": 1,
            "mode": "Pixel_Model",
        }

        dtgen = DataGenerator(**gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_arrays.X_SimplePixelCase)
        np.testing.assert_array_equal(y, test_arrays.Y_SimplePixelCase)

    def test_simple_2D_case(self):
        gen_args = {
            "path_collection_catalog": self.catalog_dict_path,
            "split": 1,
            "train": True,
            "width": 3,
            "height": 3,
            "timesteps": 3,
            "num_bands": 4,
            "batch_number": 1,
            "mode": "2D_Model",
        }

        dtgen = DataGenerator(**gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_arrays.X_Simple2DCase)
        np.testing.assert_array_equal(y, test_arrays.Y_Simple2DCase)
