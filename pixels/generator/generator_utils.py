import io
import zipfile

import backoff
import boto3
import numpy as np
import rasterio
import structlog

import pixels.generator.generator_augmentation_2D as aug
import pixels.generator.stac as pxstc

# S3 class instanciation.
s3 = boto3.client("s3")
logger = structlog.get_logger(__name__)


def open_zip_from_s3(source_path):
    """
    Read a zip file in s3.

    Parameters
    ----------
        source_path : str
            Path to the zip file on s3 containing the rasters.

    Returns
    -------
        data : BytesIO
            Obejct from the zip file.
    """
    s3_path = source_path.split("s3://")[1]
    bucket = s3_path.split("/")[0]
    path = s3_path.replace(bucket + "/", "")
    s3 = boto3.client("s3")
    data = s3.get_object(Bucket=bucket, Key=path)["Body"].read()
    data = io.BytesIO(data)
    return data


def read_img_and_meta_raster(raster_path):
    if raster_path.startswith("s3://"):
        s3_path = raster_path.split("s3://")[1]
        bucket = s3_path.split("/")[0]
        path = s3_path.replace(bucket + "/", "")
        data = s3.get_object(Bucket=bucket, Key=path)["Body"].read()
        raster_path = io.BytesIO(data)
    with rasterio.open(raster_path) as src:
        img = src.read()
        meta = src.meta
    return img, meta


def read_raster_inside_zip(file_inside_zip, source_zip_path):
    if source_zip_path.startswith("zip://s3"):
        zip_file = pxstc.open_zip_from_s3(source_zip_path.split("zip://")[-1])
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
                zip_file = pxstc.open_zip_from_s3(source_zip_path.split("zip://")[-1])
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


def do_augmentation(
    X, y, sizex, sizey, augmentation_index=1, batch_size=1, mode="3D_Model"
):
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
    if mode == "2D_Model":
        X = np.expand_dims(X, 1)
        y = np.expand_dims(y, 1)
    for batch in range(batch_size):
        augmented_X = X[batch : batch + 1]
        augmented_Y = y[batch : batch + 1]
        for i in augmentation_index:
            aug_X, aug_Y = aug.augmentation(
                X[batch : batch + 1],
                y[batch : batch + 1],
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
    if mode == "2D_Model":
        batch_X = np.vstack(batch_X)
        batch_Y = np.vstack(batch_Y)
    return batch_X, batch_Y


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
