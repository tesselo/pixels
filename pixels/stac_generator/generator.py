import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool

import boto3
import numpy as np
from tensorflow import keras

from pixels import stac_training
from pixels.exceptions import InconsistentGeneratorDataException
from pixels.stac_generator import filters, generator_augmentation_2D, generator_utils

# S3 class instanciation.
s3 = boto3.client("s3")
logger = logging.getLogger(__name__)


class DataGenerator(keras.utils.Sequence):
    """
    Defining class for generator.
    """

    def __init__(
        self,
        path_collection_catalog="",
        split=1,
        random_seed=None,
        train=True,
        timesteps=None,
        width=None,
        height=None,
        num_bands=None,
        num_classes=1,
        upsampling=1,
        mode="3D_Model",
        batch_number=1,
        padding=0,
        x_nan_value=0,
        y_nan_value=None,
        padding_mode="edge",
        dtype=None,
        augmentation=0,
    ):
        """
        Initial setup for the class.

        Parameters
        ----------
            path_collection_catalog : str
                Path to the dictonary containing the training set.
            split : float
                Value between 0 and 1. Percentage of dataset to use.
            random_seed : int
                Numpy random seed. To randomize the dataset choice.
            train : bool
                Boolean setting for output. (True: X, Y | False: X)
            timesteps : int
                Number of timesteps to use.


        """
        self.split = split
        self.random_seed = random_seed
        self.train = train
        self.batch_number = batch_number
        self.mode = mode
        self.padding_mode = padding_mode
        self.dtype = dtype
        self.augmentation = augmentation
        self.x_nan_value = x_nan_value
        self.y_nan_value = y_nan_value

        # Open and analyse collection.
        self.path_collection_catalog = path_collection_catalog
        self.parse_collection()

        # Handle image size.
        self.timesteps = timesteps
        self.num_bands = num_bands
        self.num_classes = num_classes
        self.upsampling = upsampling
        self.width = width
        self.height = height
        self.padding = padding
        if self.mode != "Pixel_Model":
            self.x_open_shape = (
                self.timesteps,
                self.num_bands,
                self.width,
                self.height,
            )
            self.y_width = self.width * self.upsampling
            self.y_height = self.height * self.upsampling
            self.y_open_shape = (1, self.y_width, self.y_height)
            self.x_width = self.y_width + (self.padding * 2)
            self.x_height = self.y_height + (self.padding * 2)
            if self.mode == "3D_Model":
                self.expected_x_shape = (
                    self.batch_number,
                    self.timesteps,
                    self.x_width,
                    self.x_height,
                    self.num_bands,
                )
                self.expected_y_shape = (
                    self.batch_number,
                    self.y_width,
                    self.y_height,
                    self.num_classes,
                )
            if self.mode == "2D_Model":
                self.expected_x_shape = (
                    self.batch_number * self.timesteps,
                    self.x_width,
                    self.x_height,
                    self.num_bands,
                )
                self.expected_y_shape = (
                    self.batch_number * self.timesteps,
                    self.y_width,
                    self.y_height,
                    self.num_classes,
                )

    def parse_collection(self):
        """
        Seting class id list based on existing catalog dictionary.
        """
        # Open the indexing dictionary.
        self.collection_catalog = stac_training._load_dictionary(
            self.path_collection_catalog
        )
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
        self.length = math.ceil(self.original_size * self.split)
        # Spliting the dataset.
        if self.random_seed and self.split < 1:
            np.random.seed(self.random_seed)
            self.id_list = np.random.choice(self.id_list, self.length, replace=False)
        elif self.split < 1:
            self.id_list = self.id_list[: self.length]

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
        x_paths = catalog["x_paths"]
        y_path = catalog["y_path"]
        if self.relative_paths:
            parent_path = os.path.dirname(self.path_collection_catalog)
            x_paths = [os.path.join(parent_path, path) for path in x_paths]
            y_path = os.path.join(parent_path, y_path)
        # TODO: Check if it is the best way to multiprocessing rabbit hole.
        with ThreadPoolExecutor(max_workers=min(len(x_paths), 12)) as executor:
            x_tensor = []
            futures = []
            for x_path in x_paths:
                futures.append(
                    executor.submit(generator_utils.read_raster_file, x_path)
                )
            # Process completed tasks.
            for future in futures:
                result = future.result()
                x_tensor.append(result)
        # Get the imgs list and the meta list.
        x_imgs = np.array(x_tensor, dtype="object")[:, 0]
        # Ensure all images are numpy arrays.
        x_imgs = np.array([np.array(x) for x in x_imgs])
        x_meta = np.array(x_tensor, dtype="object")[:, 1]
        # Same process for y data.
        if self.train:
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
        # Choose and order timesteps by level of nan_value density.
        x_tensor = filters._order_tensor_on_masks(
            np.array(x_tensor), self.x_nan_value, number_images=self.timesteps
        )
        # Ensure X img size.
        x_tensor = x_tensor[
            : self.timesteps, : self.num_bands, : self.width, : self.height
        ]
        # Fill missing pixels to the standard, with the NaN value of the object.
        if self.mode == "2D_Model":
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
        if self.train:
            # Limit the size to the maximum expected.
            y_tensor = y_tensor[: self.num_classes, : self.y_width, : self.y_height]
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
        # Bring pixel dimension to the front.
        X = np.swapaxes(X, 1, 2)
        X = np.swapaxes(X, 0, 1)
        # Compute drop mask based on X values. This
        mask_1d = np.any(X != self.x_nan_value, axis=(1, 2))
        # In training mode, reshape Y data as well.
        if self.train:
            # Flatten 2D data to 1D.
            Y = Y.ravel()
            # Ensure X and Y have the same size.
            if X.shape[0] != Y.shape[0]:
                raise InconsistentGeneratorDataException(
                    f"X and Y shape are not the same ({X.shape[0]} vs {Y.shape[0]})"
                )
            # Add Y nodata values to mask array.
            if self.y_nan_value:
                mask_1d = np.logical_and(mask_1d, Y != self.y_nan_value)
            # Drop the Y values using the combined mask.
            Y = Y[mask_1d]
            Y = np.expand_dims(Y, axis=-1)
        # Drop the X values using combined mask.
        X = X[mask_1d]
        return np.array(X), np.array(Y)

    def get_and_process(self, index):
        x_imgs, y_img = self.get_data(index, only_images=True)
        # X -> (Timesteps, num_bands, width, height)
        # Y -> (num_classes, width, height)
        # Make padded timesteps, with nan_value.
        if self.mode == "3D_Model" or self.mode == "Pixel_Model":
            if len(x_imgs) < self.timesteps:
                x_imgs = np.vstack(
                    (
                        x_imgs,
                        np.zeros(
                            (
                                self.timesteps - np.array(x_imgs).shape[0],
                                *np.array(x_imgs).shape[1:],
                            )
                        ),
                    )
                )
        if self.mode == "3D_Model" or self.mode == "2D_Model":
            # This gets the data to be used in image models.
            x_tensor, y_tensor = self.process_data(x_imgs, y_tensor=y_img)
            # Change the shape order to :
            # X -> (Timesteps, width, height, num_bands)
            # Y -> (width, height, num_classes, )
            x_tensor = np.swapaxes(x_tensor, 1, 2)
            x_tensor = np.swapaxes(x_tensor, 2, 3)
            if self.train:
                y_tensor = np.swapaxes(y_tensor, 0, 1)
                y_tensor = np.swapaxes(y_tensor, 1, 2)
        if self.mode == "Pixel_Model":
            x_tensor, y_tensor = self.process_pixels(x_imgs, Y=y_img)
        # For multiclass problems, convert the Y data to categorical.
        if self.num_classes > 1 and self.train:
            # Convert data to one-hot encoding. This assumes class DN numbers to
            # be strictly sequential and starting with 0.
            y_tensor = keras.utils.to_categorical(y_tensor, self.num_classes)
        if not self.train:
            return x_tensor
        if self.mode == "2D_Model":
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
        # Do all batches in parallel.
        with Pool(self.batch_number) as p:
            tensor = p.map(self.get_and_process, list_indexes)
        # Break down the tuple n(X, Y) into X and Y.
        if self.train:
            X = [np.array(x[0]) for x in tensor]
            Y = np.array([np.array(y[1]) for y in tensor])
        else:
            X = tensor
        X = np.array([np.array(x) for x in X])
        # Since 2D mode is a special case of 3D, it just requires a ravel on
        # 1st two dimensions.
        if self.mode == "2D_Model" or self.mode == "Pixel_Model":
            X = np.vstack(X)
            if self.train:
                Y = np.vstack(Y)
        # Enforce a dtype.
        if self.dtype:
            X = X.astype(self.dtype)
            if self.train:
                Y = Y.astype(self.dtype)
        # Augment data, for more detail see do_augmentation() on generator_utils.
        if self.augmentation > 0:
            X, Y = generator_utils.do_augmentation(
                X,
                Y,
                augmentation_index=generator_utils.augmentation,
                batch_size=self.batch_number,
            )
        # Return X only (not train) or X and Y (train).
        if not self.train:
            return X
        return X, Y
