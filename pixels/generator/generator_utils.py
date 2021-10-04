import io
import os
import zipfile
from urllib.parse import urlparse

import backoff
import boto3
import numpy as np
import rasterio
import structlog

logger = structlog.get_logger(__name__)


def open_object_from_s3(source_path):
    # In multiprocessing each worker must open its own connection.
    s3 = boto3.client("s3")
    s3_path = source_path.split("s3://")[1]
    bucket = s3_path.split("/")[0]
    path = s3_path.replace(bucket + "/", "")
    data = s3.get_object(Bucket=bucket, Key=path)["Body"].read()
    data = io.BytesIO(data)
    return data


def download_object_from_s3(uri, folder_to_save_files):
    s3 = boto3.client("s3")
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
    save_path = os.path.join(folder_to_save_files, key)
    if not os.path.exists(save_path):
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        s3.download_file(bucket, key, save_path)
    return save_path


def read_img_and_meta_raster(raster_path):
    if isinstance(raster_path, str) and raster_path.startswith("s3://"):
        raster_path = open_object_from_s3(raster_path)
    with rasterio.open(raster_path) as src:
        img = src.read()
        meta = src.meta
    return img, meta


def read_raster_inside_zip(file_inside_zip, source_zip_path):
    if source_zip_path.startswith("zip://s3"):
        zip_file = open_object_from_s3(source_zip_path.split("zip://")[-1])
    else:
        zip_file = source_zip_path
    zip_file = zipfile.ZipFile(zip_file, "r")
    raster_file = zip_file.read(file_inside_zip)
    raster_file = io.BytesIO(raster_file)
    return read_img_and_meta_raster(raster_file)


def read_raster_inside_opened_zip(file_inside_zip, zip_file):
    raster_file = zip_file.read(file_inside_zip)
    raster_file = io.BytesIO(raster_file)
    return read_img_and_meta_raster(raster_file)


@backoff.on_exception(
    backoff.fibo,
    rasterio.errors.RasterioIOError,
    max_tries=8,
)
def read_raster_file(path_raster):
    if path_raster.startswith("zip:"):
        source_zip_path = path_raster.split("!/")[0]
        file_inside_zip = path_raster.split("!/")[-1]
        return read_raster_inside_zip(file_inside_zip, source_zip_path)
    else:
        raster_file = path_raster
    return read_img_and_meta_raster(raster_file)


def read_raster_meta(path_raster):
    try:
        if path_raster.startswith("zip:"):
            source_zip_path = path_raster.split("!/")[0]
            file_inside_zip = path_raster.split("!/")[-1]
            if source_zip_path.startswith("zip://s3"):
                zip_file = open_object_from_s3(source_zip_path.split("zip://")[-1])
            zip_file = zipfile.ZipFile(zip_file, "r")
            raster_file = zip_file.read(file_inside_zip)
            raster_file = io.BytesIO(raster_file)
        else:
            raster_file = path_raster
        with rasterio.open(raster_file, driver="GTiff") as src:
            meta = src.meta
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
        tensor = np.concatenate((tensor, np.full(tuple(final_shape), value)), axis=dim)
    return tensor


def multiclass_builder(Y, class_definition, max_number):
    """
    Makes a linear array into a multiclass array.
    Takes the array Y, either a list or a integer.
    Parameters
    ----------
        Y : numpy array
            Goal image in training.
        class_definition : int or list
            Values to define the Y classes. If int is a number of classes, if a list it is the classes.
        max_number : float
            Maximun possible value on training data.

    Returns
    -------
        multiclass_y: numpy array
            Classified image.
    """
    if isinstance(class_definition, int):
        # Linear division of value with class_definition classes.
        multiclass_y = Y / (max_number / class_definition)
    else:
        class_definition = np.sort(np.unique(class_definition))
        multiclass_y = np.copy(Y)
        # Make brackets of classes.
        class_number = 0
        multiclass_y[Y <= class_definition[0]] = class_number
        for value in class_definition[1:]:
            down_value = class_definition[class_number]
            class_number += 1
            multiclass_y[np.logical_and(Y > down_value, Y <= value)] = class_number
        multiclass_y[Y > class_definition[-1]] = class_number + 1

    return multiclass_y.astype("int")


def class_sample_weights_builder(label, class_weights):
    # Create the image with the weights.
    return np.take(class_weights, label)
