import json
import math
import os
import tempfile
from typing import List, Protocol, Union

import numpy as np
from tensorflow import keras

from pixels import tio
from pixels.const import LANDSAT_8, SENTINEL_2
from pixels.exceptions import InconsistentGeneratorDataException, PixelsException
from pixels.generator import augmentation, filters
from pixels.generator.generator_utils import (
    class_sample_weights_builder,
    fill_missing_dimensions,
    multiclass_builder,
)
from pixels.generator.types import (
    XShape,
    XShape1D,
    XShape2D,
    XShape3D,
    YShape,
    YShape1D,
    YShapeND,
)
from pixels.log import BoundLogger, logger
from pixels.path import Path
from pixels.utils import run_concurrently

# Mode Definitions
GENERATOR_MODE_TRAINING = "training"
GENERATOR_MODE_PREDICTION = "prediction"
GENERATOR_MODE_EVALUATION = "evaluation"
GENERATOR_3D_MODEL = "3D_Model"
GENERATOR_2D_MODEL = "2D_Model"
GENERATOR_PIXEL_MODEL = "Pixel_Model"
GENERATOR_PIXEL_VECTOR_MODEL = "Pixel_Vector_Model"
GENERATOR_RESNET_2D_MODEL = "RESNET_2D_Model"
GENERATOR_RESNET_3D_MODEL = "RESNET_3D_Model"
GENERATOR_RESNET_IMG_2D_MODEL = "RESNET_IMG_2D_Model"
GENERATOR_RESNET_IMG_3D_MODEL = "RESNET_IMG_3D_Model"

# Groups of modes.
GENERATOR_2D_MODES = [
    GENERATOR_2D_MODEL,
    GENERATOR_RESNET_2D_MODEL,
    GENERATOR_RESNET_IMG_2D_MODEL,
]
GENERATOR_3D_MODES = [
    GENERATOR_3D_MODEL,
    GENERATOR_RESNET_3D_MODEL,
    GENERATOR_RESNET_IMG_3D_MODEL,
]
GENERATOR_RESNET_IMG_MODES = [
    GENERATOR_RESNET_IMG_3D_MODEL,
    GENERATOR_RESNET_IMG_2D_MODEL,
]
GENERATOR_RESNET_VALUE_MODES = [
    GENERATOR_RESNET_2D_MODEL,
    GENERATOR_RESNET_3D_MODEL,
]
GENERATOR_RESNET_MODES = [
    *GENERATOR_RESNET_IMG_MODES,
    *GENERATOR_RESNET_VALUE_MODES,
]
GENERATOR_UNET_MODEL = [GENERATOR_2D_MODEL, GENERATOR_3D_MODEL]
GENERATOR_X_IMAGE_MODES = [
    *GENERATOR_3D_MODES,
    *GENERATOR_2D_MODES,
    *GENERATOR_RESNET_IMG_MODES,
]
GENERATOR_Y_IMAGE_MODES = [*GENERATOR_UNET_MODEL, *GENERATOR_RESNET_IMG_MODES]
GENERATOR_Y_VALUE_MODES = [
    GENERATOR_RESNET_2D_MODEL,
    GENERATOR_RESNET_3D_MODEL,
    GENERATOR_PIXEL_VECTOR_MODEL,
]


class Generator(keras.utils.Sequence, BoundLogger):
    """
    Defining class for generator.
    """

    def __init__(
        self,
        path_collection_catalog="",
        split=1,
        random_seed=None,
        timesteps=None,
        width=None,
        height=None,
        y_width=None,
        y_height=None,
        num_bands=None,
        num_classes=1,
        upsampling=1,
        mode=GENERATOR_3D_MODEL,
        batch_number=1,
        padding=0,
        y_padding=0,
        x_nan_value=0,
        y_nan_value=None,
        nan_value=None,
        padding_mode="edge",
        dtype=None,
        augmentation=0,
        training_percentage=1,
        usage_type=GENERATOR_MODE_TRAINING,
        class_definitions=None,
        y_max_value=None,
        class_weights=None,
        download_data=False,
        download_dir=None,
        normalization=None,
        shuffle=True,
        one_hot=True,
        cloud_sort=False,
        framed_window=3,
    ):
        """
        Initial setup for the class.
        Bahamut eyes: https://bahamut.slab.com/posts/data-generator-specification-vbeitb77
        """
        self.split = split
        self.random_seed = random_seed
        self.batch_number = batch_number
        self.mode = mode
        self.padding_mode = padding_mode
        self.dtype = dtype
        self.augmentation = augmentation
        self.x_nan_value = x_nan_value
        self.y_nan_value = y_nan_value
        self.training_percentage = training_percentage
        self.usage_type = usage_type
        self.normalization = normalization
        self.shuffle = shuffle
        self.one_hot = one_hot
        self.cloud_sort = cloud_sort
        if self.usage_type != GENERATOR_MODE_TRAINING:
            self.shuffle = False

        super().__init__(
            log_id=logger.log_id,
            context={"mode": mode, "usage_type": usage_type, "data_type": dtype},
        )

        # Multiclass transform.
        self.class_definitions = class_definitions
        self.y_max_value = y_max_value
        if isinstance(class_definitions, int) and not y_max_value:
            raise InconsistentGeneratorDataException(
                "For multiclass builder with number of classes, a y_max_value must be provided."
            )

        self.nan_value = nan_value
        if not nan_value:
            self.nan_value = y_nan_value

        self.path_collection_catalog = path_collection_catalog
        # Open the indexing dictionary.
        self.collection_catalog = tio.load_dictionary(self.path_collection_catalog)

        if download_data:
            temp_dir = None
            if not download_dir:
                temp_dir = tempfile.TemporaryDirectory()
                download_dir = temp_dir.name
            self.download_and_parse_data(download_dir)
            if temp_dir:
                temp_dir.cleanup()
        self.parse_collection()

        # Image Origins.
        self.platforms = set()
        self.bands = {}
        self.init_collection_sources()

        # Handle image size.
        # Not for 2D
        self.timesteps = timesteps
        #
        # ALL
        self.num_bands = num_bands
        self.num_classes = num_classes
        #
        # Not for pixel mode
        self.upsampling = upsampling
        self.width = width
        self.height = height
        self.y_width = y_width
        self.y_height = y_height
        self.padding = padding
        self.y_padding = y_padding
        #

        # only Resnet
        if framed_window % 2 == 0:
            framed_window += 1
        self.framed_window = framed_window
        #

        # Discriminate vector / raster, maybe one property fits all
        # maybe self.source
        self.y_zip = None
        self.y_geojson = None
        #
        # Only multiclass
        self.class_weights = class_weights
        if self.one_hot and self.class_weights:
            weights_sum = sum(class_weights.values())
            self.class_weights = np.array(
                [f / weights_sum for f in class_weights.values()]
            )
        #
        self.define_shapes()

    @property
    def train(self):
        return (
            self.usage_type == GENERATOR_MODE_TRAINING
            or self.usage_type == GENERATOR_MODE_EVALUATION
        )

    @property
    def multiclass_maker(self):
        # TODO: clarify responsibility(this makes classes cry out of whatever)
        return (self.class_definitions is not None) and self.train

    def define_shapes(self):
        raise NotImplementedError

    def download_and_parse_data(self, download_dir):
        # Is only done if download_data
        # TODO: fucking break it down into shit pieces, refactor.
        if not tio.is_remote(self.path_collection_catalog):
            self.warning("Data can only be downloaded if on remote storage.")
            return

        self.info(
            f"Download all data from {os.path.dirname(self.path_collection_catalog)}"
        )
        list_of_tifs = tio.list_files(
            os.path.dirname(self.path_collection_catalog), suffix=".tif"
        )
        self.info(f"Downloading {len(list_of_tifs)} images")
        # Download the Pixels Data images in parallel.
        run_concurrently(
            tio.download,
            variable_arguments=list_of_tifs,
            static_arguments=[download_dir],
        )
        # Retrieve path for training data.
        y_path_file = self.collection_catalog[list(self.collection_catalog.keys())[0]][
            "y_path"
        ]
        parsed_y_path_file = Path(y_path_file)
        # Create a string from collection_catalog. Easier to change equal parts on all dictionary.
        collection_catalog_str = json.dumps(self.collection_catalog)

        if tio.is_archive_parsed(parsed_y_path_file):
            y_path_file = tio.download(parsed_y_path_file.archive, download_dir)
            with tio.open_zip(y_path_file) as z:
                z.extractall(y_path_file.replace(".zip", ""))
            # Inside the catalog change the y_path, from rasterio and remote reading format
            # to absolute downloaded path.
            collection_catalog_str = collection_catalog_str.replace(
                "zip://", ""
            ).replace(".zip!", "")
        if y_path_file.endswith("geojson"):
            tio.download(y_path_file, download_dir)
        bucket_name = self.path_collection_catalog.split("/")[2]
        # Change paths in collection catalog.
        collection_catalog_str = collection_catalog_str.replace(
            f"s3://{bucket_name}", download_dir
        )
        self.collection_catalog = json.loads(collection_catalog_str)
        self.info("Download of all data completed.")

    def init_collection_sources(self):
        """
        Read the collection config to set used platforms and bands.
        """
        # Making this a list will help in future implementation with multiple sources.
        path_collection = os.path.dirname(os.path.dirname(self.path_collection_catalog))
        path_collection_config = os.path.join(path_collection, "config.json")
        if not tio.file_exists(path_collection_config):
            self.warning("Collection config file not found.")
            return
        collection_config = tio.load_dictionary(path_collection_config)
        platform = collection_config["platforms"]
        self.platforms.add(platform)
        self.bands[platform] = collection_config["bands"]

    def parse_collection(self):
        """
        Set class id list based on existing catalog dictionary.
        """
        if self.usage_type in [GENERATOR_MODE_PREDICTION, GENERATOR_MODE_TRAINING]:
            self.training_percentage = self.split
        # The ids are the names of each image collection.
        self.original_id_list = list(self.collection_catalog.keys())
        # Check if path names are relative (to catalog dictionary) or absolute.
        if "relative_paths" in self.original_id_list:
            self.relative_paths = self.collection_catalog["relative_paths"]
            self.original_id_list.remove("relative_paths")
        else:
            self.relative_paths = False

        # Original size of dataset, all the images collections available.
        self.original_size = len(self.original_id_list)
        # This is the length of ids to use.
        training_length = math.ceil(self.original_size * self.training_percentage)
        # Split the dataset.
        # The splitting must be done in separate for random and not.
        # Otherwise, the resulting list when not random has a random order.
        # And that makes it possible for overlapping ids in batch processes.
        if self.random_seed:
            np.random.seed(self.random_seed)
            training_id_list = np.random.choice(
                self.original_id_list, training_length, replace=False
            )
        else:
            training_id_list = self.original_id_list[:training_length]

        # Split the dataset to unused data.
        if self.usage_type == GENERATOR_MODE_EVALUATION:
            evaluation_id_list = np.setdiff1d(self.original_id_list, training_id_list)
            requested_evaluation_length = (
                math.floor(self.original_size * self.split) or 1
            )

            if requested_evaluation_length > len(evaluation_id_list):
                self.warning(
                    "The requested evaluation data length is bigger than the total evaluation set. Using only full evaluation set."
                )

            evaluation_id_list = evaluation_id_list[:requested_evaluation_length]

            self.length = len(evaluation_id_list)
            self.id_list = evaluation_id_list
        else:
            self.length = len(training_id_list)
            self.id_list = training_id_list

        # Shuffle data to help the fitting process.
        if self.shuffle:
            np.random.shuffle(self.id_list)

    def __len__(self):
        # The return value is the actual generator size, the number of times it
        # can be called.
        return math.ceil(self.length / self.batch_number)

    def get_data(self, index, metadata=False):
        """
        Get the img and metadata based on the index paths.
        If it is a training set, returns X and Y. If not only returns X.

        Parameters
        ----------
            index : int
                Index value on id_list to fetch the data.
            metadata: bool
                Determines if the metadata will be fetched

        Returns
        -------
            x_imgs : numpy tensor
                Array with loaded X images(Timesteps, num_bands, width, height).
            y_img : numpy tensor
                Array with loaded Y images(num_classes, width, height).
            x_meta: array of dictionaries
                Array containing all the X metadata dictionaries.
            y_meta: dict
                Dictionary with Y metadata.
        """
        # TODO: Study source flow differences and discriminators
        # Get the collected id from the index list and its catalog from the
        # index dictionary.
        x_id = self.id_list[index]
        catalog = self.collection_catalog[x_id]
        x_paths = list(np.unique(catalog["x_paths"]))
        y_path = catalog["y_path"]
        x_paths = np.sort(x_paths)
        x_paths = x_paths[max(len(x_paths) - self.timesteps, 0) :]
        if self.relative_paths:
            parent_path = os.path.dirname(self.path_collection_catalog)
            x_paths = [os.path.join(parent_path, path) for path in x_paths]
            y_path = os.path.join(parent_path, y_path)
        # Download images in parallel.
        temp_dir = None
        if tio.is_remote(x_paths[0]):
            temp_dir = tempfile.TemporaryDirectory()
            download_dir = temp_dir.name
            downloaded = run_concurrently(
                tio.download,
                variable_arguments=x_paths,
                static_arguments=[download_dir],
            )
        else:
            downloaded = x_paths
        x_imgs = []
        x_meta = []
        for image in downloaded:
            raster = tio.read_raster(image)
            x_imgs.append(np.array(raster.img))
            x_meta.append(np.array(raster.meta))
        if temp_dir:
            temp_dir.cleanup()
        x_imgs = np.array(x_imgs)

        if (
            SENTINEL_2 in self.platforms or LANDSAT_8 in self.platforms
        ) and self.cloud_sort:
            # Now we only use one platform.
            sat_platform = [f for f in self.platforms][0]
            x_imgs = filters.order_tensor_on_cloud_mask(
                x_imgs, max_images=self.timesteps, sat_platform=sat_platform
            )

        if not self.train:
            if metadata:
                return x_imgs, x_meta
            return x_imgs, None

        parsed_y_path = Path(y_path)
        if tio.is_archive_parsed(parsed_y_path):
            if self.y_zip is None:
                self.y_zip = tio.open_zip(parsed_y_path)
            raster = tio.read_raster(y_path, zip_object=self.y_zip)
            y_img = raster.img
            y_meta = raster.meta

        elif y_path.endswith("geojson") and self.mode in GENERATOR_Y_VALUE_MODES:
            import geopandas as gp

            if self.y_geojson is None:
                y_file = tio.get(y_path)
                self.y_geojson = gp.read_file(y_file)
            id_x = int([f for f in x_id.split("_") if f.isnumeric()][0])
            y_img = self.y_geojson.iloc[id_x]["class"]
            y_meta = None
        else:
            raster = tio.read_raster(y_path)
            y_img = raster.img
            y_meta = raster.meta
        y_img = np.array(y_img)
        if metadata:
            return x_imgs, y_img, x_meta, y_meta
        return x_imgs, y_img

    def get_meta(self, index):
        """
        Processing of data on 3D and 2D modes.
        """

        x_id = self.id_list[index]
        catalog = self.collection_catalog[x_id]
        x_paths = catalog["x_paths"]
        x_meta = tio.read_raster_meta(x_paths[0])
        if self.train:
            y_path = catalog["y_path"]
            y_meta = tio.read_raster_meta(y_path)
            return x_meta, y_meta
        return x_meta

    def process_data(self, x_tensor, y_tensor=None):
        """
        Processing of data on 3D and 2D modes.
        """
        # ACHTUNG: only Pixel does not use this, study swag and flow
        # Ensure X img size.
        x_tensor = x_tensor[
            : self.timesteps, : self.num_bands, : self.height, : self.width
        ]
        # Fill missing pixels to the standard, with the NaN value of the object.
        if self.mode in GENERATOR_2D_MODES:
            # In 2D mode we don't want to fill missing timesteps.
            self.x_open_shape = (x_tensor.shape[0], *self.x_open_shape[1:])
        if x_tensor.shape != self.x_open_shape:
            x_tensor = fill_missing_dimensions(x_tensor, self.x_open_shape)
        # Upsample the X.
        if self.upsampling > 1:
            x_tensor = augmentation.upscale_multiple_images(
                x_tensor, upscale_factor=self.upsampling
            )
        # Add padding.
        if self.padding > 0:
            x_tensor = np.pad(
                x_tensor,
                (
                    (0, 0),
                    (0, 0),
                    (self.padding, self.padding),
                    (self.padding, self.padding),
                ),
                mode=self.padding_mode,
            )
        # Ensure correct size of Y data in training mode.
        if self.train and self.mode in GENERATOR_Y_IMAGE_MODES:
            # Turn to multiclass.
            if self.multiclass_maker:
                y_tensor = multiclass_builder(
                    y_tensor, self.class_definitions, self.y_max_value, self.y_nan_value
                )
            # Using last class for nan-values.
            if (
                self.y_nan_value
                and self.mode in GENERATOR_UNET_MODEL
                and self.num_classes > 1
                and not self.class_definitions
            ):
                if self.y_nan_value not in np.arange(self.num_classes):
                    y_tensor[y_tensor == self.y_nan_value] = self.num_classes - 1
            # Limit the size to the maximum expected.
            y_tensor = y_tensor[: self.num_classes, : self.y_height, : self.y_width]
            # Fill the gaps with nodata if the array is too small.
            if y_tensor.shape != self.y_open_shape:
                y_tensor = fill_missing_dimensions(y_tensor, self.y_open_shape)
        return x_tensor, y_tensor

    def process_resnet_img(self, X, Y=None):
        """
        Processing of data on Resnet img mode.

        Parameters
        ----------
            X : numpy tensor
                Tensor containing the collected X images.
            Y : numpy tensor
                Tensor containing the collected Y images.

        Returns
        -------
            x_train_imgs : numpy tensor
                Tensor with every framed pixel.
            y_pixels : numpy tensor
                Tensor with every valid pixel.
        """
        pad_size = int((self.framed_window - 1) / 2)
        padded_x_img = np.pad(
            X,
            (
                (0, 0),
                (pad_size, pad_size),
                (pad_size, pad_size),
                (0, 0),
            ),
            mode="edge",
        )
        y_pixels = []
        x_train_imgs = []
        moving_window_start = 0
        moving_window_end_h = self.height * self.upsampling
        moving_window_end_w = self.width * self.upsampling
        if self.train:
            moving_window_start += pad_size
            moving_window_end_h -= pad_size
            moving_window_end_w -= pad_size
        for h in range(moving_window_start, moving_window_end_h):
            for w in range(moving_window_start, moving_window_end_w):
                if Y is not None:
                    y_pixel = Y[h, w, :]
                    if np.all(y_pixel == self.y_nan_value):
                        continue
                    y_pixels.append(y_pixel)

                x_train_img = padded_x_img[
                    :, h : h + self.framed_window, w : w + self.framed_window, :
                ]
                x_train_imgs.append(x_train_img)
        x_train_imgs = np.array(x_train_imgs)
        if self.train:
            y_pixels = np.array(y_pixels)
            x_train_imgs, unique_indexes = np.unique(
                x_train_imgs, axis=0, return_index=True
            )
            y_pixels = y_pixels[unique_indexes]
        return x_train_imgs, y_pixels

    def process_pixels(self, X, Y=None):
        """
        Processing of data on Pixel mode.
        """
        # Flatten the with and height into single pixel 1D. The X tensor at
        # this point has shape (time, bands, width, height).
        x_new_shape = (X.shape[0], X.shape[1], X.shape[2] * X.shape[3])
        X = X.reshape(x_new_shape)
        # Ensure X img timesteps and bands.
        X = X[: self.timesteps, : self.num_bands]
        # Fill in missing dimensions.
        x_new_shape = (self.timesteps, self.num_bands, x_new_shape[2])
        X = fill_missing_dimensions(X, x_new_shape)
        # Bring pixel dimension to the front.
        X = np.swapaxes(X, 1, 2)
        X = np.swapaxes(X, 0, 1)
        # Compute drop mask based on X values. This
        mask_1d = np.any(X != self.x_nan_value, axis=(1, 2))
        # In training mode, reshape Y data as well.
        if self.train:
            # Flatten 2D data to 1D.
            Y = Y.ravel()
            # Add Y nodata values to mask array.
            if self.y_nan_value:
                mask_1d = np.logical_and(mask_1d, Y != self.y_nan_value)
            # Drop the Y values using the combined mask.
            Y = Y[mask_1d]
            # Create dimension on last axis.
            Y = np.expand_dims(Y, axis=-1)
        # Drop the X values using combined mask.
        X = X[mask_1d]
        # Ensure X and Y have the same size.
        if self.train:
            if X.shape[0] != Y.shape[0]:
                raise InconsistentGeneratorDataException(
                    f"X and Y shape are not the same ({X.shape[0]} vs {Y.shape[0]})"
                )
        return np.array(X), np.array(Y)

    def get_and_process(self, index):
        # TODO: study flows and swags

        x_imgs, y_img = self.get_data(index, metadata=False)
        # X -> (Timesteps, num_bands, width, height)
        # Y -> (num_classes, width, height)
        # Make padded timesteps, with nan_value.
        if self.mode in [*GENERATOR_3D_MODES, GENERATOR_PIXEL_MODEL]:
            if len(x_imgs) < self.timesteps:
                x_imgs = np.vstack(
                    (
                        x_imgs,
                        np.zeros(
                            (
                                self.timesteps - np.array(x_imgs).shape[0],
                                *np.array(x_imgs).shape[1:],
                            ),
                            dtype=x_imgs.dtype,
                        ),
                    )
                )
        # Choose and order timesteps by level of nan_value density.
        x_imgs = filters.order_tensor_on_masks(
            np.array(x_imgs), self.x_nan_value, max_images=self.timesteps
        )
        if self.mode in GENERATOR_X_IMAGE_MODES:
            # This gets the data to be used in image models.
            x_tensor, y_tensor = self.process_data(x_imgs, y_tensor=y_img)
            # Change the shape order to :
            # X -> (Timesteps, width, height, num_bands)
            # Y -> (width, height, num_classes, )
            x_tensor = np.swapaxes(x_tensor, 1, 2)
            x_tensor = np.swapaxes(x_tensor, 2, 3)
            if self.train and self.mode in GENERATOR_Y_IMAGE_MODES:
                y_tensor = np.swapaxes(y_tensor, 0, 1)
                y_tensor = np.swapaxes(y_tensor, 1, 2)
        elif self.mode == GENERATOR_PIXEL_MODEL:
            x_tensor, y_tensor = self.process_pixels(x_imgs, Y=y_img)
        else:
            raise PixelsException(
                f"Pixels mode {self.mode} not supported in get_and_process"
            )
        if self.mode in GENERATOR_RESNET_IMG_MODES:
            x_tensor, y_tensor = self.process_resnet_img(x_tensor, Y=y_tensor)
        # For multiclass problems, convert the Y data to categorical.
        if self.num_classes > 1 and self.train and self.one_hot:
            # Convert data to one-hot encoding. This assumes class DN numbers to
            # be strictly sequential and starting with 0.
            y_tensor = keras.utils.to_categorical(y_tensor, self.num_classes)
        if not self.train:
            return x_tensor
        if self.mode in GENERATOR_2D_MODES:
            y_tensor = np.repeat(np.array([y_tensor]), x_tensor.shape[0], axis=0)
        return x_tensor, y_tensor

    def __getitem__(self, index):
        """
        Generate batch of data.

        Parameters
        ----------
            index : int
                Index value on id_list to fetch the data.

        Returns
        -------
            X : numpy tensor
                Array with processed X images. Can choose 3 modes:
                    3D_Model:
                        (Batch_number, timesteps, width, height, num_bands).
                    2D_Model:
                        (Batch_number * timesteps, width, height, num_bands).
                    Pixel_Model:
                        (Batch_number * width * height, timesteps, num_bands).
                    RESNET_IMG_3D_Model:
                        (Batch_number, timesteps, frame_width, frame_height, num_bands).
                    RESNET_IMG_2D_Model:
                        (Batch_number * timesteps, frame_width, frame_height, num_bands).
            Y : numpy tensor (optional)
                Array with loaded Y images(num_classes, width, height).
                    3D_Model:
                        (Batch_number, width, height, num_classes).
                    2D_Model:
                        (Batch_number * timestep, width, height, num_classes).
                    Pixel_Model:
                        (Batch_number * width * height, num_classes).
                    RESNET_IMG_3D_Model:
                        (Batch_number * frame_width * frame_height, num_classes).
                    RESNET_IMG_2D_Model:
                        (Batch_number * timesteps * frame_width * frame_height, num_bands).
        """
        # TODO: study flows and swags

        # Build a list of indexes to grab.
        list_indexes = [
            (f * len(self)) + index
            for f in np.arange(self.batch_number)
            if ((f * len(self)) + index) < self.original_size
        ]
        tensor = []
        # Loop on batch number.
        for ind in list_indexes:
            if ind >= len(self.id_list):
                continue
            tensor.append(self.get_and_process(ind))
        # Break down the tuple n(X, Y) into X and Y.
        if self.train:
            X = [np.array(x[0]) for x in tensor]
            Y = np.array([np.array(y[1]) for y in tensor])
        else:
            X = tensor
        X = np.stack(X, axis=0)
        # Since 2D mode is a special case of 3D, it just requires a ravel on
        # 1st two dimensions.
        if self.mode in [
            *GENERATOR_2D_MODES,
            GENERATOR_PIXEL_MODEL,
            *GENERATOR_RESNET_IMG_MODES,
        ]:
            X = np.vstack(X)
            if self.train:
                Y = np.vstack(Y)
        # Augment data, for more detail see do_augmentation_on_batch() on generator_utils.
        if self.augmentation > 0 and self.mode in GENERATOR_Y_IMAGE_MODES:
            X, Y = augmentation.do_augmentation_on_batch(
                X,
                Y,
                augmentation_index=self.augmentation,
                batch_size=len(X),
                sizeX_height=self.x_height,
                sizeX_width=self.x_width,
                sizeY_height=self.y_height,
                sizeY_width=self.y_width,
                mode=self.mode,
            )
        if self.normalization is not None:
            # Normalize data to [0, 1].
            X = np.clip(X, 0, self.normalization) / self.normalization
        # Enforce a dtype.
        if self.dtype:
            X = X.astype(self.dtype)
            if self.train:
                Y = Y.astype(self.dtype)
        wrong_x_shape = False
        wrong_y_shape = False
        if len(X.shape) != len(self.expected_x_shape):
            wrong_x_shape = True
        if self.train:
            if len(Y.shape) != len(self.expected_y_shape):
                wrong_y_shape = True
        if wrong_x_shape or wrong_y_shape:
            x_id = self.id_list[index]
            catalog = self.collection_catalog[x_id]
            x_paths = list(np.unique(catalog["x_paths"]))
            x_paths = np.unique([os.path.dirname(f) for f in x_paths])[0]
            y_path = catalog["y_path"]
            self.warning(f"Item at index {index} did not manage to make it trough.")
            if wrong_x_shape:
                self.warning(f"X files failed: {x_paths}.")
            if wrong_y_shape:
                self.warning(f"Y file failed: {y_path}.")
            if index == len(self) - 1:
                new_index = index - 1
            else:
                new_index = index + 1
            if self.class_weights is not None:
                X, Y, sample_weights = self.__getitem__(new_index)
            elif not self.train:
                X = self.__getitem__(new_index)
            else:
                X, Y = self.__getitem__(new_index)
        # Return X only (not train) or X and Y (train).
        if not self.train:
            return X
        if self.class_weights is not None and self.one_hot:
            sample_weights = class_sample_weights_builder(
                np.argmax(Y, axis=-1), self.class_weights
            )
            return X, Y, sample_weights
        return X, Y

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.id_list)


class ImageGenerator(Generator):
    # outputs x and y as images
    def define_shapes(self):
        self.x_open_shape = (
            self.timesteps,
            self.num_bands,
            self.height,
            self.width,
        )
        if not self.y_width and not self.y_height:
            self.y_width = self.width * self.upsampling
            self.y_height = self.height * self.upsampling
        self.y_open_shape = (1, self.y_height, self.y_width)
        self.y_width = self.y_width + (self.y_padding * 2)
        self.y_height = self.y_height + (self.y_padding * 2)
        self.x_width = (self.width * self.upsampling) + (self.padding * 2)
        self.x_height = (self.height * self.upsampling) + (self.padding * 2)

        if self.mode == GENERATOR_2D_MODEL:
            self.expected_x_shape = (
                self.batch_number * self.timesteps,
                self.x_height,
                self.x_width,
                self.num_bands,
            )
            self.expected_y_shape = (
                self.batch_number * self.timesteps,
                self.y_height,
                self.y_width,
                self.num_classes,
            )

        if self.mode == GENERATOR_3D_MODEL:
            self.expected_x_shape = (
                self.batch_number,
                self.timesteps,
                self.x_height,
                self.x_width,
                self.num_bands,
            )
            self.expected_y_shape = (
                self.batch_number,
                self.y_height,
                self.y_width,
                self.num_classes,
            )


class PixelGenerator(Generator):
    # outputs x and y as value (pixel mode)
    def define_shapes(self):
        self.expected_x_shape = (
            self.batch_number,
            self.timesteps,
            self.num_bands,
        )
        self.expected_y_shape = (
            self.batch_number,
            self.num_classes,
        )


class NetGenerator(Generator):
    # outputs x as image and y as value (resnet mode)
    def define_shapes(self):
        self.x_open_shape = (
            self.timesteps,
            self.num_bands,
            self.height,
            self.width,
        )
        if not self.y_width and not self.y_height:
            self.y_width = self.width * self.upsampling
            self.y_height = self.height * self.upsampling
        self.y_open_shape = (1, self.y_height, self.y_width)
        self.y_width = self.y_width + (self.y_padding * 2)
        self.y_height = self.y_height + (self.y_padding * 2)
        self.x_width = (self.width * self.upsampling) + (self.padding * 2)
        self.x_height = (self.height * self.upsampling) + (self.padding * 2)

        if self.mode == GENERATOR_RESNET_2D_MODEL:
            self.expected_x_shape = (
                self.batch_number * self.timesteps,
                self.x_height,
                self.x_width,
                self.num_bands,
            )
            self.expected_y_shape = (
                self.batch_number * self.timesteps,
                self.num_classes,
            )
        if self.mode == GENERATOR_RESNET_IMG_3D_MODEL:
            self.expected_x_shape = (
                self.batch_number,
                self.timesteps,
                self.framed_window,
                self.framed_window,
                self.num_bands,
            )
            self.expected_y_shape = (
                self.batch_number,
                self.num_classes,
            )


class Generator:
    def __init__(self) -> None:
        pass
        # self.data_handler = DataHandler()

    def define_shapes(self):
        raise NotImplementedError

    def read_data(self):
        self.data_handler.load
        raise NotImplementedError

    def process_data(self):
        raise NotImplementedError


class Data(Protocol):
    x_tensor: np.array
    y_tensor: np.array

    x_shape: XShape
    y_shape: YShape

    def from_numpy(cls, nparray: np.array) -> "Data":
        ...

    def from_tiff(cls, path: str) -> "Data":
        ...

    def from_vector(cls, path: str) -> "Data":
        ...

    def augment(self, augmentation_index: Union[int, List] = 0):
        self.x_tensor, self.y_tensor = augmentation.do_augmentation_on_batch(
            self.x_tensor,
            self.y_tensor,
            self.x_shape,
            self.y_shape,
            augmentation_index=augmentation_index,
        )

    def upsample(self, upscale_factor: int = 1):
        self.x_tensor = augmentation.upscale_multiple_images(
            self.x_tensor, upscale_factor
        )

    def padd(self, padding: int = 0, padding_mode="same"):
        # Add padding.
        if padding > 0:
            self.x_tensor = np.pad(
                self.x_tensor,
                (
                    (0, 0),
                    (0, 0),
                    (padding, padding),
                    (padding, padding),
                ),
                mode=padding_mode,
            )

    def cloud_sort(self):
        ...

    def normalize(self, normalization: float = None):
        if normalization is not None:
            # Normalize data to [0, 1].
            self.x_tensor = np.clip(self.x_tensor, 0, normalization) / normalization

    def force_dtype(self, dtype):
        self.x_tensor = self.x_tensor.astype(dtype)
        self.y_tensor = self.y_tensor.astype(dtype)

    def fill(self):
        ...

    def shrink(self):
        ...

    def process():
        raise NotImplementedError


class Data3D(Data):
    def __init__(self, x_shape: XShape3D, y_shape: YShapeND):
        self.x_shape = x_shape
        self.y_shape = y_shape


class Data2D(Data):
    def __init__(self, x_shape: XShape2D, y_shape: YShapeND):

        self.x_shape = x_shape
        self.y_shape = y_shape


class Data1D(Data):
    def __init__(self, x_shape: XShape1D, y_shape: YShape1D):
        self.x_shape = x_shape
        self.y_shape = y_shape


class LearningMode:
    def __init__():
        pass

    def process_data(self):
        raise NotImplementedError

    def show_data(self):
        print(self.X)

    def __getitem__(self, index):
        return self.X, self.Y, self.weights

    def list_to_use(self):
        raise


class TrainingMode(LearningMode):
    def __init__(self):
        self.X = "2"
        self.Y = "1"


class EvalMode(LearningMode):
    def __init__(self):
        self.X = "2"
        self.Y = "1"


class PredictMode(LearningMode):
    def __getitem__(self, index):
        return self.X

    def predict():
        pass
