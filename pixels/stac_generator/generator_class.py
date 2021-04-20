import io
import logging
import math
import os
import pprint
import zipfile
from multiprocessing import Pool
from urllib.parse import urlparse

import boto3
import numpy as np
import pystac
import rasterio
from pystac import STAC_IO
from rasterio.errors import RasterioIOError
from tensorflow import keras

import pixels.stac as pxstc
import pixels.stac_generator.filters as pxfl
import pixels.stac_generator.generator_augmentation_2D as aug
import pixels.stac_generator.visualizer as vis
import pixels.stac_training as stctr
from pixels.exceptions import InconsistentGeneratorDataException, InvalidGeneratorConfig

# S3 class instanciation.
s3 = boto3.client("s3")
logger = logging.getLogger(__name__)


def read_item_raster(path):
    """
    Read all data from a raster file.
    """
    # Open raster.
    with rasterio.open(path) as src:
        # Read and return raster data.
        return src.read()


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
        nan_value=None,
        mask_band=False,
        random_seed=None,
        num_classes=1,
        batch_number=1,
        train_split=None,
        num_bands=10,
        augmentation=0,
        dtype=None,
        y_downsample=[],
        padding=0,
        padding_mode="edge",
        x_nan_value=None,
        y_nan_value=None,
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
        self.dtype = dtype
        self.num_bands = num_bands
        self.augmentation = augmentation
        self.y_downsample = y_downsample
        self.padding = padding
        self.padding_mode = padding_mode
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
        self.x_nan_value = x_nan_value
        self.y_nan_value = y_nan_value
        if y_nan_value:
            # Ensure Y nan_value is not 0.
            if y_nan_value == 0:
                raise InvalidGeneratorConfig("Y nan value must not be 0.")
            if y_nan_value > 0 and y_nan_value < self.num_classes:
                raise InvalidGeneratorConfig(
                    "Y nan value must not be within the num_classes range."
                )
        self._set_definition()
        self._check_get_catalogs_indexing()
        # Check if batch size.
        if self.batch_number > 1 and not self.train:
            raise InvalidGeneratorConfig("Batch size needs to be 1 for prediction.")
        # Log the entire config.
        config = {
            "path_collection": self.path_collection,
            "split": self.split,
            "train": self.train,
            "upsampling": self.upsampling,
            "timesteps": self.timesteps,
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "prediction_catalog": self.prediction,
            "nan_value": self.nan_value,
            "mask_band": self.mask_band,
            "random_seed": self.random_seed,
            "num_classes": self.num_classes,
            "batch_number": self.batch_number,
            "train_split": self.train_split,
            "num_bands": self.num_bands,
            "augmentation": self.augmentation,
            "dtype": self.dtype,
            "y_downsample": self.y_downsample,
            "padding": self.padding,
            "padding_mode": self.padding_mode,
            "x_nan_value": self.x_nan_value,
            "y_nan_value": self.y_nan_value,
        }
        logger.info(f"Generator config: {pprint.pformat(config, indent=4)}")

    def _set_definition(self):
        # TODO: Read number of bands from somewhere.
        self._original_num_bands = self.num_bands
        if not self.y_nan_value:
            self.y_nan_value = self.nan_value
        if not self.x_nan_value:
            self.x_nan_value = self.nan_value
        if self.mask_band:
            self.num_bands = self.num_bands + 1
        if self.mode == "Pixel_Model":
            self.augmentation = 0
            self.upsampling = False
            self.padding = 0
            self.expected_x_shape = (
                self.batch_number * self.width * self.height,
                self.timesteps,
                self.num_bands,
            )
            self.expected_y_shape = (
                self.batch_number * self.width * self.height,
                self.num_classes,
            )

        if self.upsampling:
            self._orignal_width = self.width
            self._orignal_height = self.height
            self.width = int(math.ceil(self.width * self.upsampling))
            self.height = int(math.ceil(self.height * self.upsampling))
            self.x_width = self.width + (self.padding * 2)
            self.x_height = self.height + (self.padding * 2)
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
                self.width,
                self.height,
                self.num_classes,
            )
        if self.prediction:
            if isinstance(self.prediction, str):
                self.prediction = pystac.Catalog.from_file(self.prediction)
        if not self.train:
            self.augmentation = 0

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
            if self.train:
                np.random.seed(self.random_seed)
                indexes = np.random.choice(
                    len(self.collection.get_child_links()),
                    self._original_size,
                    replace=False,
                )
            if self.train_split and self.train_split != 1:
                np.random.seed(self.random_seed)
                indexes = np.random.choice(
                    len(self.collection.get_child_links()),
                    int(len(self.collection.get_child_links()) * self.train_split),
                    replace=False,
                )
                indexes = np.setdiff1d(
                    np.arange(len(self.collection.get_child_links())), indexes
                )
                if len(indexes) > self._original_size:
                    np.random.seed(self.random_seed)
                    indexes = np.random.choice(
                        indexes, self._original_size, replace=False
                    )
                elif len(indexes) < self._original_size:
                    np.random.seed(self.random_seed)
                    new_ind = np.random.choice(
                        np.setdiff1d(np.arange(self._original_size), indexes),
                        self._original_size - len(indexes),
                    )
                    indexes = np.concatenate([indexes, new_ind])
        else:
            indexes = np.arange(self._original_size)
        for catalog in self.collection.get_children():
            y_index = int(
                os.path.dirname(catalog.get_links("corresponding_y")[0].target)
                .split("/")[-1]
                .split("_")[-1]
            )
            if y_index in self.y_downsample:
                continue
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
        self.length = int(
            math.ceil(
                (self._original_size - len(self.y_downsample)) / self.batch_number
            )
        )
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
        if not value and value != 0:
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
        From the paths list get the raster info. Sets the right timestep.
        Order the timesteps based on a mask, removes extras, or padds when lacking.

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
        y_tensor = np.array(y_img)
        if self.train and len(y_tensor.shape) == 3:
            # Change y raster from (num_bands, wdt, hgt) to (wdt, hgt, num_classes).
            y_tensor = y_tensor.swapaxes(0, 1)
            y_tensor = y_tensor.swapaxes(1, 2)

        # Return only some metadata if requested.
        if search_for_meta:
            with rasterio.open(x_paths[0]) as src:
                return src.meta

        # Open all X images in parallel.
        with Pool(min(len(x_paths), 12)) as p:
            x_tensor = p.map(read_item_raster, x_paths)

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
        x_tensor = pxfl._order_tensor_on_masks(
            np.array(x_tensor), self.x_nan_value, number_images=self.timesteps
        )
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
        for i in range(3):
            try:
                X, Y = self.get_data(
                    self.catalogs_dict[catalog_id]["x_paths"],
                    self.catalogs_dict[catalog_id]["y_path"],
                )
                break
            except RasterioIOError:
                logger.warning(f"Rasterio IO error, trying again. try number: {i}.")

        if self.mode == "3D_Model":
            # Ensure correct size of Y data in training mode.
            if self.train:
                # The Y open shape should always be 1D before converting to
                # categorical.
                y_target_shape = (self.width, self.height, 1)
                # Limit the size to the maximum expected.
                Y = Y[: self.width, : self.height, :]
                # Fill the gaps with nodata if the array is too small.
                if Y.shape != y_target_shape:
                    self._wrong_sizes_list.append(index)
                    Y = self._fill_missing_dimensions(Y, y_target_shape)
                    logger.warning(f"Y dimensions not suitable in index {index}.")
                # Limit the size again to ensure final shape.
                Y = Y[: self.width, : self.height, :]
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
            # Add band for NaN mask.
            if self.mask_band:
                if not self.train:
                    mask_shp = list(X.shape)
                    mask_shp[1] = 1
                    mask_img = np.ones(tuple(mask_shp))
                else:
                    mask_img = np.array([Y[:, :, 0]]) != self.nan_value
                    mask_img = np.repeat([mask_img], self.timesteps, axis=0)
                mask_band = mask_img.astype("int")
                X = np.hstack([X, mask_band])

        if self.mode == "Pixel_Model":
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
            # Drop the X values using combined mask.
            X = X[mask_1d]

        # For multiclass problems, convert the Y data to categorical.
        if self.num_classes > 1:
            # Convert data to one-hot encoding. This assumes class DN numbers to
            # be strictly sequential and starting with 0.
            Y = keras.utils.to_categorical(Y, self.num_classes)
            # Swap axes so that the class index axis is first.
            Y = np.squeeze(np.swapaxes(Y, 0, -1))

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

    def do_augmentation(self, X, y, augmentation_index=1, batch_size=1):
        """
        Define how many augmentations to do, and build the correct input for the augmentation function

        Parameters
        ----------
            X : numpy array
                Set of collected images.
            Y : numpy array
                Goal image in training.
            augmentation_index : int or list
                Set the number of augmentations. If list, does the augmentatios
                with the keys on the list, if int, does all the keys up to that.
                keys:
                    0: No augmentation
                    1, 2, 3: flips
                    4: noise
                    5: bright
        Returns
        -------
            augmentedX, augmentedY : numpy array
                Augmented images.
        """
        if isinstance(augmentation_index, int):
            augmentation_index = np.arange(augmentation_index) + 1
        if self.mode == "3D_Model":
            batchX = np.array([])
            batchY = np.array([])
            for batch in range(batch_size):
                augmentedX = np.array([X[batch]])
                augmentedY = np.array([y[batch]])
                for i in augmentation_index:
                    augX, augY = aug.augmentation(
                        np.array([X[batch]]),
                        np.array([y[batch]]),
                        sizex=self.x_width,
                        sizey=self.x_height,
                        augmentation_index=i,
                    )
                    augmentedX = np.concatenate([augmentedX, augX])
                    augmentedY = np.concatenate([augmentedY, augY])
                if not batchX.any():
                    batchX = augmentedX
                    batchY = augmentedY
                else:
                    batchX = np.concatenate([batchX, augmentedX])
                    batchY = np.concatenate([batchY, augmentedY])
        return np.array(batchX), np.array(batchY)

    def __getitem__(self, index):
        """
        Generate one batch of data
        """
        final_batch_number = self.batch_number
        index_count = index
        for i in range(self.batch_number):
            if index_count >= len(self.id_list):
                final_batch_number = i
                # X = np.concatenate([X,x])
                # Y = np.concatenate([Y,y])
                continue
            try:
                x, y = self.get_data_from_index(index_count)
            except:
                # Try again 5 times
                for t in range(5):
                    try:
                        x, y = self.get_data_from_index(index_count + t + 1)
                        break
                    except Exception as E:
                        logger.warning(f"Try number {t}. {E}")
            # Add padding.
            if self.padding > 0:
                x = np.pad(
                    x,
                    (
                        (0, 0),
                        (0, 0),
                        (self.padding, self.padding),
                        (self.padding, self.padding),
                    ),
                    mode=self.padding_mode,
                )
            # (Timesteps, bands, img) -> (Timesteps, img, Bands)
            # For channel last models: otherwise uncoment.
            # TODO: add the data_format mode based on model using.
            if self.mode == "3D_Model":
                x = np.swapaxes(x, 1, 2)
                x = np.array([np.swapaxes(x, 2, 3)])
                y = np.array([y])
            if i == 0:
                X = x
                Y = y
            else:
                X = np.vstack([X, x])
                Y = np.vstack([Y, y])
            # X.append(x)
            # Y.append(y)
            index_count = index_count + len(self)
        if self.mode == "3D_Model":
            X = np.array(X)
            expected_x_shape = (final_batch_number, *self.expected_x_shape[1:])
            if X.shape != expected_x_shape:
                self._wrong_sizes_list.append(index_count)
                X = self._fill_missing_dimensions(X, expected_x_shape)
                logger.warning(f"X dimensions not suitable in index {index_count}.")
            Y = np.array(Y)
            expected_y_shape = (final_batch_number, *self.expected_y_shape[1:])
            if self.train and Y.shape != expected_y_shape:
                self._wrong_sizes_list.append(index_count)
                Y = self._fill_missing_dimensions(Y, expected_y_shape)
                logger.warning(f"Y dimensions not suitable in index {index_count}.")
            # Hacky way to ensure data, must change.
            if len(X.shape) < 4:
                logger.warning(
                    f"X shape insuficient, going to next item with index {index_count + 1}."
                )
                self.__getitem__(index_count + 1)
        if self.dtype:
            X = X.astype(self.dtype)
            if self.train:
                Y = Y.astype(self.dtype)

        if self.augmentation > 0:
            X, Y = self.do_augmentation(
                X, Y, augmentation_index=self.augmentation, batch_size=self.batch_number
            )
        if not self.train:
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
            if not X.shape[-2:] == Y[:, :, 0].shape[-2:]:
                X = aug.upscale_multiple_images(X)
            if self.mode == "3D_Model":
                y = np.array([Y])
            if self.mask_band:
                mask = X[:1, -1:, :, :]
                X = X[:, :-1, :, :]
                mask = np.repeat(mask, X.shape[1], axis=1)
                mask = mask * scaling
                X = np.vstack([X, mask])
        if in_out == "OUT":
            X, Y = self.__getitem__(index)
            y = Y
            if self.mask_band:
                mask = X[:, :1, :, :, -1:]
                X = X[:, :, :, :, :-1]
                mask = np.repeat(mask, X.shape[-1], axis=-1)
                mask = mask * scaling
                X = np.hstack([X, mask])
            if self.padding > 0:
                y = np.pad(
                    y,
                    (
                        (0, 0),
                        (self.padding, self.padding),
                        (self.padding, self.padding),
                        (0, 0),
                    ),
                    mode="constant",
                )
        if self.prediction:
            pred_img = self.get_prediction_from_index(index)
        vis.visualize_in_item(
            X, y, RGB=RGB, scaling=scaling, in_out=in_out, prediction=pred_img
        )
