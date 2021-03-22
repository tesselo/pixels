import io
import logging
import math
import os
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
import pixels.stac_generator.filters as pxfl
import pixels.stac_training as stctr

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
        nan_value=-9999,
        mask_band=False,
        random_seed=None,
        num_classes=1,
        batch_number=1,
        train_split=None,
        num_bands=10,
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
        self.random_seed = random_seed
        self.num_classes = num_classes
        self.batch_number = batch_number
        self.train_split = train_split
        self.train = train
        self.num_bands = num_bands
        self._set_s3_variables(path_collection)
        self._set_collection(path_collection)
        self.upsampling = upsampling
        self.timesteps = timesteps
        self.mode = mode
        self.width = width
        self.height = height
        self.prediction = prediction_catalog
        self.nan_value = nan_value
        self.mask_band = mask_band
        self._wrong_sizes_list = []
        self._set_definition()
        self._check_get_catalogs_indexing()

    def _set_definition(self):
        # TODO: Read number of bands from somewhere.
        self._original_num_bands = self.num_bands
        if self.mask_band:
            self.num_bands = self.num_bands + 1
        if self.upsampling:
            self._orignal_width = self.width
            self._orignal_height = self.height
            self.width = int(math.ceil(self.width * self.upsampling))
            self.height = int(math.ceil(self.height * self.upsampling))
        if self.mode == "3D_Model":
            self.expected_x_shape = (
                self.batch_number,
                self.timesteps,
                self.width,
                self.height,
                self.num_bands,
            )
            self.expected_y_shape = (
                self.batch_number,
                self.num_classes,
                self.width,
                self.height,
            )
        if self.prediction:
            if isinstance(self.prediction, str):
                self.prediction = pystac.Catalog.from_file(self.prediction)

    def _check_get_catalogs_indexing(self):
        dict_path = os.path.join(
            os.path.dirname(self.path_collection), "catalogs_dict.json"
        )
        dict_exists = False
        if self.path_collection.startswith("s3"):
            dict_exists = pxstc.check_file_in_s3(dict_path)
        else:
            dict_exists = os.path.exists(dict_path)
        if dict_exists:
            self.catalogs_dict = stctr._load_dictionary(dict_path)

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
        len(self)
        self.id_list = []
        count = 0
        # Build a list of indexes, choosing randomly.
        if self.random_seed:
            np.random.seed(self.random_seed)
            if self.train:
                indexes = np.random.choice(
                    len(self.collection.get_child_links()),
                    self._original_size,
                    replace=False,
                )
            if self.train_split:
                indexes = np.random.choice(
                    len(self.collection.get_child_links()),
                    int(len(self.collection.get_child_links()) * self.train_split),
                    replace=False,
                )
                indexes = np.setdiff1d(
                    np.arange(len(self.collection.get_child_links())), indexes
                )
                if len(indexes) > self._original_size:
                    indexes = np.random.choice(
                        indexes, self._original_size, replace=False
                    )
                elif len(indexes) < self._original_size:
                    new_ind = np.random.choice(
                        np.setdiff1d(np.arange(self._original_size), indexes),
                        self._original_size - len(indexes),
                    )
                    indexes = np.concatenate([indexes, new_ind])
        else:
            indexes = np.arange(self._original_size)
        for catalog in self.collection.get_children():
            if count not in indexes:
                if count > max(indexes):
                    break
                count = count + 1
                continue
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
        self._original_size = int(len(self.collection.get_child_links()) * self.split)
        self.length = int(math.ceil(self._original_size / self.batch_number))
        # For 2D:
        # self.length = 0
        # for child in self.collection.get_children():
        #     self.length = self.length + len(child.get_item_links())
        return self.length

    def _fill_missing_dimensions(self, tensor, expected_shape, value=None):
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
        if not value:
            value = self.nan_value
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
            if self.num_classes > 1:
                y_img = np.squeeze(
                    np.swapaxes(keras.utils.to_categorical(y_img), 0, -1)
                )
        except Exception as E:
            logger.warning(f"Generator error in get_data: {E}")
            y_img = None
        x_tensor = []
        y_tensor = np.array(y_img)
        for x_p in x_paths:
            with rasterio.open(x_p) as src:
                x_img = np.array(src.read())
                x_tensor.append(x_img)
                if search_for_meta:
                    return src.meta
                src.close()
            # y_tensor.append(np.array(y_img))
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
            x_tensor = pxfl._order_tensor_on_masks(np.array(x_tensor), self.nan_value)
            x_tensor = np.array(x_tensor)[: self.timesteps]
            y_tensor = np.array(y_tensor)
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
        if "prediction_path" not in self.catalogs_dict[catalog_id]:
            if self.prediction:
                try:
                    pred_path = (
                        self.prediction.get_item(catalog_id)
                        .get_assets()[catalog_id]
                        .href
                    )
                except:
                    pred_path = None
                self.catalogs_dict[catalog_id]["prediction_path"] = pred_path
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
        # Check if the loaded images have the needed dimensions.
        # Cut or add NaN values on surplus/missing pixels.
        # Treat X, then test for Y, treat Y.
        x_open_shape = (
            self.timesteps,
            self._original_num_bands,
            self._orignal_width,
            self._orignal_height,
        )
        # Remove extra pixels.
        X = X[:, :, : self._orignal_width, : self._orignal_height]
        # Fill missing pixels to the standard, with the NaN value of the object.
        if X.shape != x_open_shape:
            self._wrong_sizes_list.append(index)
            X = self._fill_missing_dimensions(X, x_open_shape)
            logger.warning(f"X dimensions not suitable in index {index}.")
        # Upsample the X.
        if self.upsampling:
            X = X[:, :, : self._orignal_width, : self._orignal_height]
            X = aug.upscale_multiple_images(X, upscale_factor=self.upsampling)
        # Remove extra pixels.
        X = X[:, :, : self.width, : self.height]
        # Y is not None treat Y.
        if Y.any():
            y_open_shape = (self.num_classes, self.width, self.height)
            Y = Y[:, : self.width, : self.height]
            if Y.shape != y_open_shape:
                self._wrong_sizes_list.append(index)
                Y = self._fill_missing_dimensions(Y, y_open_shape)
                logger.warning(f"Y dimensions not suitable in index {index}.")
            Y = Y[:, : self.width, : self.height]
        # Add band for NaN mask.
        if self.mask_band:
            mask_img = Y != self.nan_value
            mask_img = np.repeat([mask_img], self.timesteps, axis=0)
            if not self.train:
                mask_shp = list(X.shape)
                mask_shp[1] = 1
                mask_img = np.ones(tuple(mask_shp))
            mask_band = mask_img.astype("int")
            X = np.hstack([X, mask_band])
        return X, Y

    def get_prediction_from_index(self, index, search_for_meta=False):
        if not self.prediction:
            return None
        catalog_id = self.id_list[index]
        if catalog_id not in self.catalogs_dict:
            meta = self.get_data_from_index(index, search_for_meta=True)
        pred_path = self.catalogs_dict[catalog_id]["prediction_path"]
        if not pred_path:
            return None
        with rasterio.open(pred_path) as src:
            prediction_img = src.read()
            meta = src.meta
        if search_for_meta:
            return meta
        return prediction_img

    def __getitem__(self, index):
        """
        Generate one batch of data
        """
        X = []
        Y = []
        x = np.ones(self.expected_x_shape[1:])
        y = np.ones(self.expected_y_shape[1:])
        index_count = index
        for i in range(self.batch_number):
            if index_count >= len(self.id_list):
                X.append(x)
                Y.append(y)
                continue
            x, y = self.get_data_from_index(index_count)
            # (Timesteps, bands, img) -> (Timesteps, img, Bands)
            # For channel last models: otherwise uncoment.
            # TODO: add the data_format mode based on model using.
            x = np.swapaxes(x, 1, 2)
            x = np.swapaxes(x, 2, 3)
            X.append(x)
            Y.append(y)
            index_count = index_count + len(self)
        if self.mode == "3D_Model":
            X = np.array(X)
            if X.shape != self.expected_x_shape:
                self._wrong_sizes_list.append(index_count)
                X = self._fill_missing_dimensions(X, self.expected_x_shape)
                logger.warning(f"X dimensions not suitable in index {index_count}.")
            Y = np.array(Y)
            if Y.any():
                if Y.shape != self.expected_y_shape:
                    self._wrong_sizes_list.append(index_count)
                    Y = self._fill_missing_dimensions(Y, self.expected_y_shape)
                    logger.warning(f"Y dimensions not suitable in index {index_count}.")
            # Hacky way to ensure data, must change.
            if len(X.shape) < 4:
                self.__getitem__(index_count + 1)
        if not Y.any() or not self.train:
            return X
        return X, Y

    def get_item_metadata(self, index):
        meta = self.get_data_from_index(index, search_for_meta=True)
        return meta

    def visualize_data(self, index, RGB=[2, 1, 0], scaling=4000, in_out="IN"):
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
        pred_img = None
        if in_out == "IN":
            X, Y = self.get_data_from_index(index)
            if not X.shape[-2:] == Y[0].shape[-2:]:
                X = aug.upscale_multiple_images(X)
            if self.mode == "3D_Model":
                y = Y[0]
            if self.mask_band:
                mask = X[:1, -1:, :, :]
                X = X[:, :-1, :, :]
                mask = np.repeat(mask, X.shape[1], axis=1)
                mask = mask * scaling
                X = np.vstack([X, mask])
        if in_out == "OUT":
            X, Y = self.__getitem__(index)
            y = Y[0]
            if self.mask_band:
                mask = X[:, :1, :, :, -1:]
                X = X[:, :, :, :, :-1]
                mask = np.repeat(mask, X.shape[-1], axis=-1)
                mask = mask * scaling
                X = np.hstack([X, mask])
        if self.prediction:
            pred_img = self.get_prediction_from_index(index)
        vis.visualize_in_item(
            X, y, RGB=RGB, scaling=scaling, in_out=in_out, prediction=pred_img
        )
