from urllib.parse import urlparse

import boto3
import numpy as np
import pystac
import rasterio
from pystac import STAC_IO
from tensorflow import keras

import pixels.stac as pxstc

# S3 class instanciation.
s3 = boto3.client("s3")


class DataGenerator_stac(keras.utils.Sequence):
    """
    Defining class for generator.
    """

    def __init__(self, path_collection, split=1, train=True):
        """
        Initial setup for the class.

        Parameters
        ----------
            path_collection : str
                Path to the collection containing the training set.

        """
        self.path_collection = path_collection
        self._set_s3_variables(path_collection)
        self._set_collection(path_collection)

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
            if not pxstc.check_file_in_s3(path_collection):
                # Raise Error
                print("file not found")
                return
            self.bucket = parsed.netloc
            self.collection_key = parsed.path[1:]
            STAC_IO.read_text_method = pxstc.stac_s3_read_method
            STAC_IO.write_text_method = pxstc.stac_s3_write_method

    def _set_collection(self, path_collection):
        self.collection = pystac.Collection.from_file(path_collection)

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
        self.length = len(self.collection.get_child_links())
        # For 2D:
        # self.length = 0
        # for child in self.collection.get_children():
        #     self.length = self.length + len(child.get_item_links())
        return self.length

    def get_items_paths(self, x_catalog):
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
            x_paths.append(item.get_self_href())
        y_path = x_catalog.get_links("corresponding_y")[0].target
        return x_paths, y_path

    def get_data(self, x_paths, y_path):
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
                List with all the images in the catalog.
            y_img : numpy array
                Numpy array with the y raster.
        """
        with rasterio.open(y_path) as src:
            y_img = src.read()

        x_tensor = []
        for x_p in x_paths:
            with rasterio.open(x_p) as src:
                x_tensor.append(np.array(src.read()))

        return np.array(x_tensor), np.array(y_img)
