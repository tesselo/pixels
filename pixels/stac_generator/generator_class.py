import io
import logging
import math
import zipfile
from urllib.parse import urlparse

import boto3
import numpy as np
import pystac
import rasterio
from pystac import STAC_IO
from tensorflow import keras

import pixels.generator.generator_augmentation_2D as aug
import pixels.generator.visualizer as vis
import pixels.stac as pxstc

# S3 class instanciation.
s3 = boto3.client("s3")
logger = logging.getLogger(__name__)


class DataGenerator_stac(keras.utils.Sequence):
    """
    Defining class for generator.
    """

    def __init__(
        self,
        path_collection,
        split=1,
        train=True,
        upsampling=False,
        timesteps=12,
        width=32,
        height=32,
        mode="3D_Model",
        prediction_catalog=False,
        nan_value=0,
        mask_band=False,
    ):
        """
        Initial setup for the class.

        Parameters
        ----------
            path_collection : str
                Path to the collection containing the training set.

        """
        self.path_collection = path_collection
        self.split = split
        self.catalogs_dict = {}
        self._set_s3_variables(path_collection)
        self._set_collection(path_collection)
        self.upsampling = upsampling
        self.timesteps = timesteps
        self.mode = mode
        self.width = width
        self.height = height
        self.train = train
        self.prediction = prediction_catalog
        self.nan_value = nan_value
        self.mask_band = mask_band
        self._set_definition()

    def _set_definition(self):
        # TODO: Read number of bands from somewhere.
        self.num_bands = 10
        if self.mask_band:
            self.num_bands = self.num_bands + 1
        if self.upsampling:
            self._orignal_width = self.width
            self._orignal_height = self.height
            self.width = int(math.ceil(self.width * self.upsampling))
            self.height = int(math.ceil(self.height * self.upsampling))
        if self.mode == "3D_Model":
            self.expected_x_shape = (
                1,
                self.timesteps,
                self.width,
                self.height,
                self.num_bands,
            )
            self.expected_y_shape = (1, self.timesteps, self.width, self.height, 1)
        if self.prediction:
            if isinstance(self.prediction, str):
                self.prediction = pystac.Catalog.from_file(self.prediction)

    def _set_s3_variables(self, path_collection):
        """
        Initial setup, creates s3 variables if file is in s3.

        Parameters
        ----------
            path_collection : str
                Path to the collection containing the training set.

        """
        parsed = urlparse(path_collection)
        if parsed.scheme == "s3":
            # if not pxstc.check_file_in_s3(path_collection):
            # Raise Error
            #    print("file not found")
            #    return
            self.bucket = parsed.netloc
            self.collection_key = parsed.path[1:]
            STAC_IO.read_text_method = pxstc.stac_s3_read_method
            STAC_IO.write_text_method = pxstc.stac_s3_write_method

    def _set_collection(self, path_collection):
        self.collection = pystac.Collection.from_file(path_collection)
        self.id_list = []
        count = 0
        for catalog in self.collection.get_children():
            if count >= len(self):
                break
            self.id_list.append(catalog.id)
            count = count + 1
        self.source_y_path = self.collection.get_links("origin_files")[0].target
        if self.source_y_path.endswith("zip"):
            source_y_data = pxstc.open_zip_from_s3(self.source_y_path)
            self.file_in_zip = zipfile.ZipFile(source_y_data, "r")

    def __len__(self):
        """
        Denotes the number of batches per epoch.
        Each step is a file read, which means that the total number of steps is the number of files avaible
        (data_base_size * split).
        It will vary from mode:
        pixel mode, image[2D] mode, images[2D+time] mode
        for now just the 3D mode.
        """
        # For 3D mode:
        self.length = int(len(self.collection.get_child_links()) * self.split)
        # For 2D:
        # self.length = 0
        # for child in self.collection.get_children():
        #     self.length = self.length + len(child.get_item_links())
        return self.length

    def _fill_missing_dimensions(self, tensor, expected_shape, value=0):
        """
        Fill a tensor with any shape (smaller dimensions than expected), with
        value to fill up until has the expected_shape dimensions.

        Parameters
        ----------
            tensor : numpy array
                Numpy array, X or Y object.
            expected_shape : tuple
                Shape to be expected to output on given dataset.
            value : int (float), optional
                Value to fill the gaps, defaults to zero.

        Returns
        -------
            tensor : numpy array
                Modified numpy array.

        """
        missing_shape = tuple(x1 - x2 for (x1, x2) in zip(expected_shape, tensor.shape))
        for dim in range(len(tensor.shape)):
            current_shape = tensor.shape
            final_shape = np.array(current_shape)
            final_shape[dim] = missing_shape[dim]
            tensor = np.concatenate(
                (tensor, np.full(tuple(final_shape), value)), axis=dim
            )
        return tensor

    def get_items_paths(self, x_catalog, search_for_item=False):
        """
        From a catalog get the paths for each item and the corresponding y.

        TODO: Predict mode not sending y_path, or send an empty one

        Parameters
        ----------
            x_catalog : pystac object catalog
                Catalog with multiple items.

        Returns
        -------
            x_paths : list str
                List paths for every item.
            y_path : str
                Path for the corresponding y.
        """
        x_paths = []
        for item in x_catalog.get_items():
            x_paths.append(item.assets[item.id].href)
            if search_for_item:
                return item
        try:
            y_item_path = x_catalog.get_links("corresponding_y")[0].target
            y_item = pystac.Item.from_file(y_item_path)
            y_path = y_item.assets[y_item.id].href
        except Exception as E:
            logger.warning(f"Generator error in get_items_paths: {E}")
            y_path = None
        return x_paths, y_path

    def get_data(self, x_paths, y_path, search_for_meta=False):
        """
        From the paths list get the raster info.

        TODO: Predict mode not sending y_path, or send an empty one

        Parameters
        ----------
            x_paths : list str
                List paths for every item.
            y_path : str
                Path for the corresponding y.

        Returns
        -------
            x_tensor : numpy array
                List with all the images in the catalog (Timesteps, bands, img).
            y_img : numpy array
                Numpy array with the y raster (Timesteps, band, img).
        """
        y_raster_file = y_path
        try:
            if y_path.startswith("zip://s3:"):
                y_raster_file = self.file_in_zip.read(y_path.split("!/")[-1])
                y_raster_file = io.BytesIO(y_raster_file)
            with rasterio.open(y_raster_file) as src:
                y_img = src.read()
                src.close()
        except Exception as E:
            logger.warning(f"Generator error in get_data: {E}")
            y_img = None
        x_tensor = []
        y_tensor = []
        for x_p in x_paths:
            with rasterio.open(x_p) as src:
                x_img = np.array(src.read())
                x_tensor.append(x_img)
                if search_for_meta:
                    return src.meta
                src.close()
            y_tensor.append(np.array(y_img))
        if self.mode == "3D_Model":
            if len(x_tensor) < self.timesteps:
                x_tensor = np.vstack(
                    (
                        x_tensor,
                        np.zeros(
                            (
                                self.timesteps - np.array(x_tensor).shape[0],
                                *np.array(x_tensor).shape[1:],
                            )
                        ),
                    )
                )
                y_tensor = np.vstack(
                    (
                        y_tensor,
                        np.zeros(
                            (
                                self.timesteps - np.array(y_tensor).shape[0],
                                *np.array(y_tensor).shape[1:],
                            )
                        ),
                    )
                )
            x_tensor = np.array(x_tensor)[: self.timesteps]
            y_tensor = np.array(y_tensor)[: self.timesteps]
        return np.array(x_tensor), np.array(y_tensor)

    def get_data_from_index(self, index, search_for_meta=False):
        """
        Generate data from index.
        """
        catalog_id = self.id_list[index]
        catalog = self.collection.get_child(catalog_id)
        if catalog_id not in self.catalogs_dict:
            x_paths, y_path = self.get_items_paths(catalog)
            self.catalogs_dict[catalog_id] = {}
            self.catalogs_dict[catalog_id]["x_paths"] = x_paths
            self.catalogs_dict[catalog_id]["y_path"] = y_path
        # (Timesteps, bands, img)
        if search_for_meta:
            meta = self.get_data(
                self.catalogs_dict[catalog_id]["x_paths"],
                self.catalogs_dict[catalog_id]["y_path"],
                search_for_meta=search_for_meta,
            )
            return meta
        X, Y = self.get_data(
            self.catalogs_dict[catalog_id]["x_paths"],
            self.catalogs_dict[catalog_id]["y_path"],
        )
        if self.upsampling:
            X = X[:, :, : self._orignal_width, : self._orignal_height]
            X = aug.upscale_multiple_images(X, upscale_factor=self.upsampling)
        # Remove extra pixels.
        X = X[:, :, : self.width, : self.height]
        Y = Y[:, :, : self.width, : self.height]
        # Add band for NaN mask.
        if self.mask_band:
            mask_img = Y != self.nan_value
            mask_band = mask_img.astype("int")
            X = np.hstack([X, mask_band])
        return X, Y

    def __getitem__(self, index):
        """
        Generate one batch of data
        """
        try:
            X, Y = self.get_data_from_index(index)
            # (Timesteps, bands, img) -> (Timesteps, img, Bands)
            # For channel last models: otherwise uncoment.
            # TODO: add the data_format mode based on model using.
            X = np.swapaxes(X, 1, 2)
            X = np.swapaxes(X, 2, 3)

            Y = np.swapaxes(Y, 1, 2)
            Y = np.swapaxes(Y, 2, 3)

            if self.mode == "3D_Model":
                X = np.array([X])
                Y = np.array([Y])
                if X.shape != self.expected_x_shape:
                    X = self._fill_missing_dimensions(X, self.expected_x_shape)
                    logger.warning(f"X dimensions not suitable in index {index}.")
                if Y.shape != self.expected_y_shape:
                    Y = self._fill_missing_dimensions(Y, self.expected_y_shape)
                    logger.warning(f"Y dimensions not suitable in index {index}.")
                # Hacky way to ensure data, must change.
                if len(X.shape) < 4:
                    self.__getitem__(index + 1)
            if Y is None or not self.train:
                return X
        except Exception as E:
            logger.warning(f"Error in get_item in index {index}: {E}")
            self.__getitem__(index + 1)
        return X, Y

    def get_item_metadata(self, index):
        meta = self.get_data_from_index(index, search_for_meta=True)
        return meta

    def visualize_data(self, index, RGB=[2, 1, 0], scaling=4000):
        """
        Visualize data.

        TODO: Get it to work with multiple Y.

        Parameters
        ----------
            index : int
                Catalog index to use.
            RGB : list
                List of RGB bands index.
            scaling : int
                Image scaling value.
        """
        X, Y = self.get_data_from_index(index)
        if not X.shape[-2:] == Y[0].shape[-2:]:
            X = aug.upscale_multiple_images(X)
        if self.mode == "3D_Model":
            y = Y[0, 0]
        vis.visualize_in_item(X, y, RGB=RGB, scaling=scaling)
