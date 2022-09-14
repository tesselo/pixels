import numpy as np
import pytest

from pixels.generator.generator import Generator
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
        "shuffle": False,
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
        gen_args = {**self.gen_args}
        gen_args["mode"] = mode
        dtgen = Generator(**gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])

    @pytest.mark.parametrize(
        "mode, batch, test_tuple",
        [
            ("3D_Model", 1, (test_arrays.X_Aug3D, test_arrays.Y_Aug3D)),
            ("3D_Model", 2, (test_arrays.X_Aug3D_batch, test_arrays.Y_Aug3D_batch)),
            ("2D_Model", 1, (test_arrays.X_Aug2D, test_arrays.Y_Aug2D)),
            ("2D_Model", 2, (test_arrays.X_Aug2D_batch, test_arrays.Y_Aug2D_batch)),
        ],
    )
    def test_augmentation(self, mode, batch, test_tuple):
        gen_args = {**self.gen_args}
        gen_args["augmentation"] = 3
        gen_args["mode"] = mode
        gen_args["batch_number"] = batch
        dtgen = Generator(**gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])

    @pytest.mark.parametrize(
        "mode, test_tuple, augmentation",
        [
            ("3D_Model", (test_arrays.X_upsampling, test_arrays.Y_upsampling), 0),
            ("2D_Model", (test_arrays.X_upsampling_2D, test_arrays.Y_upsampling_2D), 0),
            (
                "3D_Model",
                (test_arrays.X_upsampling_aug, test_arrays.Y_upsampling_aug),
                3,
            ),
            (
                "2D_Model",
                (test_arrays.X_upsampling_aug_2D, test_arrays.Y_upsampling_aug_2D),
                3,
            ),
        ],
    )
    def test_upsampling(self, mode, test_tuple, augmentation):
        gen_args = {**self.gen_args}
        gen_args["upsampling"] = 2
        gen_args["mode"] = mode
        gen_args["augmentation"] = augmentation
        dtgen = Generator(**gen_args)
        x, y = dtgen[1]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])

    @pytest.mark.parametrize(
        "mode, test_tuple",
        [
            ("3D_Model", (test_arrays.X_3D_multiclass, test_arrays.Y_3D_multiclass)),
            ("2D_Model", (test_arrays.X_2D_multiclass, test_arrays.Y_2D_multiclass)),
            (
                "Pixel_Model",
                (test_arrays.X_Pixel_multiclass, test_arrays.Y_Pixel_multiclass),
            ),
        ],
    )
    def test_multiclass(self, mode, test_tuple):
        gen_args = {**self.gen_args}
        gen_args["num_classes"] = 3
        gen_args["mode"] = mode
        dtgen = Generator(**gen_args)
        x, y = dtgen[2]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])

    @pytest.mark.parametrize(
        "mode, num_bands, timesteps, padding, test_tuple",
        [
            (
                "3D_Model",
                5,
                3,
                0,
                (test_arrays.X_3D_bands, test_arrays.Y_3D_bands),
            ),
            (
                "2D_Model",
                5,
                3,
                0,
                (test_arrays.X_2D_bands, test_arrays.Y_2D_bands),
            ),
            (
                "Pixel_Model",
                5,
                3,
                0,
                (test_arrays.X_Pixel_bands, test_arrays.Y_Pixel_bands),
            ),
            (
                "3D_Model",
                4,
                4,
                0,
                (test_arrays.X_3D_timesteps, test_arrays.Y_3D_timesteps),
            ),
            (
                "Pixel_Model",
                4,
                4,
                0,
                (test_arrays.X_Pixel_timesteps, test_arrays.Y_Pixel_timesteps),
            ),
            (
                "3D_Model",
                4,
                3,
                1,
                (test_arrays.X_3D_padding, test_arrays.Y_3D_padding),
            ),
            (
                "2D_Model",
                4,
                3,
                1,
                (test_arrays.X_2D_padding, test_arrays.Y_2D_padding),
            ),
        ],
    )
    def tests_on_option(self, mode, num_bands, timesteps, padding, test_tuple):
        gen_args = {**self.gen_args}
        gen_args["mode"] = mode
        gen_args["num_bands"] = num_bands
        gen_args["timesteps"] = timesteps
        gen_args["padding"] = padding

        dtgen = Generator(**gen_args)
        x, y = dtgen[0]
        np.testing.assert_array_equal(x, test_tuple[0])
        np.testing.assert_array_equal(y, test_tuple[1])

    def test_shuffle(self):
        gen_args = {**self.gen_args}
        dtgen_no_shuffle = Generator(**gen_args)
        gen_args["shuffle"] = True
        dtgen = Generator(**gen_args)
        dtgen.on_epoch_end()
        np.testing.assert_array_equal(
            np.sort(dtgen.id_list),
            np.sort(dtgen_no_shuffle.id_list),
        )
