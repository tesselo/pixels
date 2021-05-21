import numpy as np
import pytest

from pixels.stac_generator.generator import DataGenerator
from tests import test_arrays


class TestGenerator:
    catalog_dict_path = "tests/data/catalogs_dict.json"
    gen_args = {
        "path_collection_catalog": catalog_dict_path,
        "split": 1,
        "width": 3,
        "height": 3,
        "timesteps": 3,
        "num_bands": 4,
        "batch_number": 1,
        "mode": "3D_Model",
        "usage_type": "training",
        "random_seed": 5,
    }

    @pytest.mark.parametrize(
        "mode, test_tuple",
        [
            ("3D_Model", (test_arrays.X_Simple3DCase, test_arrays.Y_Simple3DCase)),
            (
                "Pixel_Model",
                (test_arrays.X_SimplePixelCase, test_arrays.Y_SimplePixelCase),
            ),
            ("2D_Model", (test_arrays.X_Simple2DCase, test_arrays.Y_Simple2DCase)),
        ],
    )
    def test_simple_modes(self, mode, test_tuple):
        self.gen_args["mode"] = mode
        dtgen = DataGenerator(**self.gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])

    @pytest.mark.parametrize(
        "mode, batch, test_tuple",
        [
            ("3D_Model", 1, (test_arrays.X_Aug3D, test_arrays.Y_Aug3D)),
            ("3D_Model", 2, (test_arrays.X_Aug3D_batch, test_arrays.Y_Aug3D_batch)),
            ("2D_Model", 1, (test_arrays.X_Aug2D, test_arrays.Y_Aug3D)),
            ("2D_Model", 2, (test_arrays.X_Aug2D_batch, test_arrays.Y_Aug2D_batch)),
        ],
    )
    def test_augmentation(self, mode, batch, test_tuple):
        self.gen_args["augmentation"] = 3
        self.gen_args["mode"] = mode
        self.gen_args["batch_number"] = batch
        dtgen = DataGenerator(**self.gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])
