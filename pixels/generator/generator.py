import json
import math
import os
import tempfile
import zipfile
from multiprocessing import Pool

import boto3
import numpy as np
import structlog
from tensorflow import keras

from pixels.exceptions import InconsistentGeneratorDataException
from pixels.generator import filters, generator_augmentation_2D, generator_utils
from pixels.generator.stac_utils import (
    _load_dictionary,
    list_files_in_folder,
    open_file_from_s3,
)

logger = structlog.get_logger(__name__)

# S3 class instanciation.
s3 = boto3.client("s3")

# Mode Definitions
GENERATOR_MODE_TRAINING = "training"
GENERATOR_MODE_PREDICTION = "prediction"
GENERATOR_MODE_EVALUATION = "evaluation"
GENERATOR_3D_MODEL = "3D_Model"
GENERATOR_2D_MODEL = "2D_Model"
GENERATOR_PIXEL_MODEL = "Pixel_Model"
GENERATOR_RESNET_2D_MODEL = "RESNET_2D_Model"
GENERATOR_RESNET_3D_MODEL = "RESNET_3D_Model"

# Groups of modes.
GENERATOR_2D_MODES = [GENERATOR_2D_MODEL, GENERATOR_RESNET_2D_MODEL]
GENERATOR_3D_MODES = [GENERATOR_3D_MODEL, GENERATOR_RESNET_3D_MODEL]
GENERATOR_X_IMAGE_MODES = [*GENERATOR_3D_MODES, *GENERATOR_2D_MODES]
GENERATOR_Y_IMAGE_MODES = [GENERATOR_3D_MODEL, GENERATOR_2D_MODEL]
GENERATOR_Y_VALUE_MODES = [
    GENERATOR_RESNET_2D_MODEL,
    GENERATOR_RESNET_3D_MODEL,
]


class DataGenerator(keras.utils.Sequence):
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
        if self.usage_type != GENERATOR_MODE_TRAINING:
            self.shuffle = False

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
        self.collection_catalog = _load_dictionary(self.path_collection_catalog)

        if download_data:
            temp_dir = None
            if not download_dir:
                temp_dir = tempfile.TemporaryDirectory()
                download_dir = temp_dir.name
            self.download_and_parse_data(download_dir)
            if temp_dir:
                temp_dir.cleanup()
        self.parse_collection()

        # Handle image size.
        self.timesteps = timesteps
        self.num_bands = num_bands
        self.num_classes = num_classes
        self.upsampling = upsampling
        self.width = width
        self.height = height
        self.y_width = y_width
        self.y_height = y_height
        self.padding = padding
        self.y_padding = y_padding
        self.y_zip = None
        self.y_geojson = None
        self.class_weights = class_weights
        if self.mode != GENERATOR_PIXEL_MODEL:
            if self.class_weights:
                self.class_weights = np.array(
                    [f / sum(class_weights.values()) for f in class_weights.values()]
                )
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
        # Cross checking.
        if (
            self.y_nan_value
            and self.mode in GENERATOR_Y_IMAGE_MODES
            and self.num_classes > 1
            and not self.class_definitions
        ):
            if self.y_nan_value not in np.arange(self.num_classes):
                raise InconsistentGeneratorDataException(
                    "For image classification the y_nan_value must be one the classes."
                )

    @property
    def train(self):
        return (
            self.usage_type == GENERATOR_MODE_TRAINING
            or self.usage_type == GENERATOR_MODE_EVALUATION
        )

    @property
    def multiclass_maker(self):
        return (self.class_definitions is not None) and self.train

    def download_and_parse_data(self, download_dir):
        # Data can only be downloaded from s3.
        if not self.path_collection_catalog.startswith("s3"):
            logger.warning("Data can only be downloaded if on S3.")
            return

        logger.info("Download all data")
        # List all collected images in pixelsdata folder.
        list_of_tifs = list_files_in_folder(
            os.path.dirname(self.path_collection_catalog), filetype="tif"
        )
        # Download the Pixels Data images in parallel.
        with Pool(min(len(list_of_tifs), 12)) as p:
            p.starmap(
                generator_utils.download_object_from_s3,
                zip(list_of_tifs, [download_dir] * len(list_of_tifs)),
            )
        # Retrieve path for training data.
        y_path_file = self.collection_catalog[list(self.collection_catalog.keys())[0]][
            "y_path"
        ]
        # Create a string from collection_catalog. Easier to change equal parts on all dictionary.
        collection_catalog_str = json.dumps(self.collection_catalog)
        # If the training data comes from a zip file, download and extract it.
        if y_path_file.startswith("zip"):
            # Change the file name format from the rasterio reading format to an absolute one.
            # Get only the zip, and not the first item inside the zip.
            y_path_file = y_path_file.replace("zip://", "").split("!")[0]
            y_path_file = generator_utils.download_object_from_s3(
                y_path_file, download_dir
            )
            with zipfile.ZipFile(y_path_file, "r") as zipi:
                # extract all files
                zipi.extractall(y_path_file.replace(".zip", ""))
            # Inside the catalog change the y_path, from rasterio and s3 reading format
            # to absolute downloaded path.
            collection_catalog_str = collection_catalog_str.replace(
                "zip://", ""
            ).replace(".zip!", "")
        if y_path_file.endswith("geojson"):
            y_path_file = generator_utils.download_object_from_s3(
                y_path_file, download_dir
            )
        bucket_name = self.path_collection_catalog.split("/")[2]
        # Change paths in collection catalog.
        collection_catalog_str = collection_catalog_str.replace(
            f"s3://{bucket_name}", download_dir
        )
        self.collection_catalog = json.loads(collection_catalog_str)
        logger.info("Download of all data completed.")

    def parse_collection(self):
        """
        Seting class id list based on existing catalog dictionary.
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
        self.id_list = self.original_id_list
        # Original size of dataset, all the images collections avaible.
        self.original_size = len(self.original_id_list)
        # This is the lenght of ids to use.
        length = math.ceil(self.original_size * self.training_percentage)
        # Spliting the dataset.
        # The spliting must be done in separate for random and not.
        # Otherwise the resulting list when not random has a random order.
        # And that makes it possible for overlaping ids in batch processes.
        if self.random_seed:
            np.random.seed(self.random_seed)
            self.id_list = np.random.choice(self.id_list, length, replace=False)
        else:
            self.id_list = self.id_list[:length]
        self.length = len(self.id_list)
        # Spliting the dataset to unused data.
        if self.usage_type == GENERATOR_MODE_EVALUATION:
            self.id_list = np.setdiff1d(self.original_id_list, self.id_list)
            length = math.floor(self.original_size * self.split)
            if length > len(self.id_list):
                logger.warning("The requested length is bigger than the id list size.")
            self.id_list = self.id_list[:length]
            self.length = len(self.id_list)
        # Shuffle data to help the fitting process.
        if self.shuffle:
            np.random.shuffle(self.id_list)

    def __len__(self):
        # The return value is the actual generator size, the number of times it
        # can be called.
        return math.ceil(self.length / self.batch_number)

    def get_data(self, index, only_images=True):
        """
        Get the img and meta data based on the index paths.
        If it is a training set, returns X and Y. If not only returns X.

        Parameters
        ----------
            index : int
                Index value on id_list to fetch the data.

        Returns
        -------
            x_imgs : numpy tensor
                Array with loaded X images(Timesteps, num_bands, width, height).
            y_img : numpy tensor
                Array with loaded Y images(num_classes, width, height).
            x_meta: array of dictonaries
                Array containg all the X metadata dictionaries.
            y_meta: dictonary
                Dictionary with Y metada.
        """
        # Get the collected id from the index list and its catalog from the
        # index dictionary.
        x_id = self.id_list[index]
        catalog = self.collection_catalog[x_id]
        x_paths = list(np.unique(catalog["x_paths"]))
        y_path = catalog["y_path"]
        if self.relative_paths:
            parent_path = os.path.dirname(self.path_collection_catalog)
            x_paths = [os.path.join(parent_path, path) for path in x_paths]
            y_path = os.path.join(parent_path, y_path)
        # Open all X images in parallel.
        with Pool(min(len(x_paths), 12)) as p:
            x_tensor = p.map(generator_utils.read_raster_file, x_paths)
        # Get the imgs list and the meta list.
        x_imgs = np.array(x_tensor, dtype="object")[:, 0]
        # Ensure all images are numpy arrays.
        x_imgs = np.array([np.array(x) for x in x_imgs])
        x_meta = np.array(x_tensor, dtype="object")[:, 1]
        # Same process for y data.
        if self.train:
            if y_path.startswith("zip:"):
                if self.y_zip is None:
                    # Open zip for y training:
                    source_zip_path = y_path.split("!/")[0]
                    if source_zip_path.startswith("zip://s3"):
                        zip_file = generator_utils.open_object_from_s3(
                            source_zip_path.split("zip://")[-1]
                        )
                    else:
                        zip_file = source_zip_path
                    self.y_zip = zipfile.ZipFile(zip_file, "r")
                file_inside_zip = y_path.split("!/")[-1]
                y_img, y_meta = generator_utils.read_raster_inside_opened_zip(
                    file_inside_zip, self.y_zip
                )
            elif y_path.endswith("geojson") and self.mode in GENERATOR_Y_VALUE_MODES:
                import geopandas as gp

                if self.y_geojson is None:
                    if y_path.startswith("s3"):
                        data = open_file_from_s3(y_path)
                        y_path = data["Body"]
                    self.y_geojson = gp.read_file(y_path)
                id_x = int([f for f in x_id.split("_") if f.isnumeric()][0])
                y_img = self.y_geojson.iloc[id_x]["class"]
                y_meta = None
            else:
                y_img, y_meta = generator_utils.read_raster_file(y_path)
            y_img = np.array(y_img)
            if only_images:
                return x_imgs, y_img
            return x_imgs, y_img, x_meta, y_meta
        # Current shapes:
        # X -> (Timesteps, num_bands, width, height)
        # Y -> (num_classes, width, height)
        if only_images:
            return x_imgs, None
        return x_imgs, x_meta

    def get_meta(self, index):
        """
        Processing of data on 3D and 2D modes.
        """

        x_id = self.id_list[index]
        catalog = self.collection_catalog[x_id]
        x_paths = catalog["x_paths"]
        x_meta = generator_utils.read_raster_meta(x_paths[0])
        if self.train:
            y_path = catalog["y_path"]
            y_meta = generator_utils.read_raster_meta(y_path)
            return x_meta, y_meta
        return x_meta

    def process_data(self, x_tensor, y_tensor=None):
        """
        Processing of data on 3D and 2D modes.
        """
        # Ensure X img size.
        x_tensor = x_tensor[
            : self.timesteps, : self.num_bands, : self.height, : self.width
        ]
        # Fill missing pixels to the standard, with the NaN value of the object.
        if self.mode in GENERATOR_2D_MODES:
            # In 2D mode we dont want to fill missing timesteps.
            self.x_open_shape = (x_tensor.shape[0], *self.x_open_shape[1:])
        if x_tensor.shape != self.x_open_shape:
            x_tensor = generator_utils.fill_missing_dimensions(
                x_tensor, self.x_open_shape
            )
        # Upsample the X.
        if self.upsampling > 1:
            x_tensor = generator_augmentation_2D.upscale_multiple_images(
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
                y_tensor = generator_utils.multiclass_builder(
                    y_tensor, self.class_definitions, self.y_max_value, self.y_nan_value
                )
            # Limit the size to the maximum expected.
            y_tensor = y_tensor[: self.num_classes, : self.y_height, : self.y_width]
            # Fill the gaps with nodata if the array is too small.
            if y_tensor.shape != self.y_open_shape:
                y_tensor = generator_utils.fill_missing_dimensions(
                    y_tensor, self.y_open_shape
                )
        return x_tensor, y_tensor

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
        X = generator_utils.fill_missing_dimensions(X, x_new_shape)
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
        x_imgs, y_img = self.get_data(index, only_images=True)
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
        x_imgs = filters._order_tensor_on_masks(
            np.array(x_imgs), self.x_nan_value, number_images=self.timesteps
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
        if self.mode == GENERATOR_PIXEL_MODEL:
            x_tensor, y_tensor = self.process_pixels(x_imgs, Y=y_img)
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
            Y : numpy tensor (optional)
                Array with loaded Y images(num_classes, width, height).
                    3D_Model:
                        (Batch_number, width, height, num_classes).
                    2D_Model:
                        (Batch_number * timestep, width, height, num_classes).
                    Pixel_Model:
                        (Batch_number * width * height, num_classes).
        """
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
        ]:
            X = np.vstack(X)
            if self.train:
                Y = np.vstack(Y)
        # Augment data, for more detail see do_augmentation_on_batch() on generator_utils.
        if self.augmentation > 0 and self.mode in GENERATOR_Y_IMAGE_MODES:
            X, Y = generator_augmentation_2D.do_augmentation_on_batch(
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
        # Return X only (not train) or X and Y (train).
        if not self.train:
            return X
        if self.class_weights is not None and self.mode in GENERATOR_Y_IMAGE_MODES:
            # This assumes the encoding in one-hot.
            sample_weights = generator_utils.class_sample_weights_builder(
                np.argmax(Y, axis=-1), self.class_weights
            )
            return X, Y, sample_weights
        return X, Y

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.id_list)
