import io
import logging
import zipfile

import boto3
import numpy as np
import rasterio

import pixels.stac as pxstc
import pixels.stac_generator.generator_augmentation_2D as aug

# S3 class instanciation.
s3 = boto3.client("s3")
logger = logging.getLogger(__name__)


def read_raster_file(path_raster):
    try:
        if path_raster.startswith("zip:"):
            source_zip_path = path_raster.split("!/")[0]
            file_inside_zip = path_raster.split("!/")[-1]
            if source_zip_path.startswith("zip://s3"):
                zip_file = pxstc.open_zip_from_s3(source_zip_path.split("zip://")[-1])
            zip_file = zipfile.ZipFile(zip_file, "r")
            raster_file = zip_file.read(file_inside_zip)
            raster_file = io.BytesIO(raster_file)
        else:
            raster_file = path_raster
        with rasterio.open(raster_file) as src:
            img = src.read()
            meta = src.meta
            src.close()
    except Exception as E:
        logger.warning(f"Generator error in read_raster_file: {E}")
        img = None
        meta = None
    return img, meta


def read_raster_meta(path_raster):
    try:
        if path_raster.startswith("zip:"):
            source_zip_path = path_raster.split("!/")[0]
            file_inside_zip = path_raster.split("!/")[-1]
            if source_zip_path.startswith("zip://s3"):
                zip_file = pxstc.open_zip_from_s3(source_zip_path.split("zip://")[-1])
            zip_file = zipfile.ZipFile(zip_file, "r")
            raster_file = zip_file.read(file_inside_zip)
            raster_file = io.BytesIO(raster_file)
        else:
            raster_file = path_raster
        with rasterio.open(raster_file) as src:
            meta = src.meta
            src.close()
    except Exception as E:
        logger.warning(f"Generator error in read_raster_meta: {E}")
        meta = None
    return meta

    def fill_missing_dimensions(tensor, expected_shape, value=None):
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
            value = 0
        missing_shape = tuple(x1 - x2 for (x1, x2) in zip(expected_shape, tensor.shape))
        for dim in range(len(tensor.shape)):
            current_shape = tensor.shape
            final_shape = np.array(current_shape)
            final_shape[dim] = missing_shape[dim]
            tensor = np.concatenate(
                (tensor, np.full(tuple(final_shape), value)), axis=dim
            )
        return tensor

    def do_augmentation(X, y, sizex, sizey, augmentation_index=1, batch_size=1):
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
        batch_X = np.array([])
        batch_Y = np.array([])
        for batch in range(batch_size):
            augmented_X = np.array([X[batch]])
            augmented_Y = np.array([y[batch]])
            for i in augmentation_index:
                aug_X, aug_Y = aug.augmentation(
                    np.array([X[batch]]),
                    np.array([y[batch]]),
                    sizex=sizex,
                    sizey=sizey,
                    augmentation_index=i,
                )
                augmented_X = np.concatenate([augmented_X, aug_X])
                augmented_Y = np.concatenate([augmented_Y, aug_Y])
            if not batch_X.any():
                batch_X = augmented_X
                batch_Y = augmented_Y
            else:
                batch_X = np.concatenate([batch_X, augmented_X])
                batch_Y = np.concatenate([batch_Y, augmented_Y])
        return np.array(batch_X), np.array(batch_Y)
