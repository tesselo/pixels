import glob
import json
import os
import shutil
from urllib.parse import urlparse

import boto3
import numpy as np
import pystac
import rasterio
import sentry_sdk
from pystac import STAC_IO

from pixels.exceptions import PixelsException
from pixels.log import logger


def write_method(uri, txt):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.resource("s3")
        s3.Object(bucket, key).put(Body=txt)
    else:
        STAC_IO.default_write_text_method(uri, txt)


def read_method(uri):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.resource("s3")
        obj = s3.Object(bucket, key)
        return obj.get()["Body"].read().decode("utf-8")
    else:
        return STAC_IO.default_read_text_method(uri)


def get_catalog_length(catalog_path):
    # Try opening link as collection. If this fails, try opening it as catalog.
    try:
        collection = pystac.Collection.from_file(catalog_path)
        size = len(collection.get_child_links())
    except KeyError:
        catalog = pystac.Catalog.from_file(catalog_path)
        size = len(catalog.get_item_links())
    return size


def save_dictionary(path, dictionary):
    new_path = path
    if path.startswith("s3"):
        new_path = path.replace("s3://", "tmp/")
    if not os.path.exists(new_path):
        try:
            os.makedirs(os.path.dirname(new_path))
        except OSError:
            # Directory already exists.
            pass
    with open(new_path, "w") as f:
        json.dump(dictionary, f)
    if path.startswith("s3"):
        upload_files_s3(
            os.path.dirname(new_path),
            file_type=os.path.split(path)[-1],
            delete_folder=True,
        )


def upload_files_s3(path, file_type=".json", delete_folder=True):
    """
    Upload files inside a folder to s3.
    The s3 paths most be the same as the folder.

    Parameters
    ----------
        path : str
            Path to folder containing the files to be uploaded.
        file_type : str, optional
            Filetype to upload, set to json.
        delete_folder: bool
            Determines if the origin folder should be deleted
    Returns
    -------

    """
    file_list = glob.glob(path + "**/**/*" + file_type, recursive=True)
    s3 = boto3.client("s3")
    sta = "s3:/"
    if not path.startswith("s3"):
        sta = path.split("/")[0]
        path = path.replace(sta, "s3:/")
    s3_path = path.split("s3://")[1]
    bucket = s3_path.split("/")[0]
    for file in file_list:
        key_path = file.replace(sta + "/" + bucket + "/", "")
        s3.upload_file(Key=key_path, Bucket=bucket, Filename=file)
    if delete_folder:
        shutil.rmtree(sta)


def open_file_from_s3(source_path):
    s3_path = source_path.split("s3://")[1]
    bucket = s3_path.split("/")[0]
    path = s3_path.replace(bucket + "/", "")
    s3 = boto3.client("s3")
    try:
        data = s3.get_object(Bucket=bucket, Key=path)
    except s3.exceptions.NoSuchKey as e:
        sentry_sdk.capture_exception(e)
        logger.warning(f"s3.exceptions.NoSuchKey. source_path {source_path}")
        data = None
    return data


def list_files_in_folder(uri, filetype="tif"):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        return list_files_in_s3(uri, filetype=filetype)
    else:
        return glob.glob(f"{uri}/**/*{filetype}", recursive=True)


def check_file_in_s3(uri):
    """
    Check if file exists at an S3 uri.

    Parameters
    ----------
    uri: str
        The S3 uri to check if file exists. Example: s3://my-bucket/config.json
    """
    # Split the S3 uri into components.
    parsed = urlparse(uri)
    # Ensure input is a s3 uri.
    if parsed.scheme != "s3":
        raise PixelsException("Invalid S3 uri found: {}.".format(uri))
    # Get bucket name.
    bucket = parsed.netloc
    # Get key in bucket.
    key = parsed.path[1:]
    # List objects with that key.
    s3 = boto3.client("s3")
    objects = s3.list_objects_v2(Bucket=bucket, Prefix=os.path.dirname(key))
    list_obj = [ob["Key"] for ob in objects["Contents"]]

    return key in list_obj


def check_file_exists(path_to_file):
    if path_to_file.startswith("s3"):
        file_check = check_file_in_s3(path_to_file)
    else:
        file_check = os.path.exists(path_to_file)
    return file_check


def upload_obj_s3(uri, obj):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.client("s3")
        s3.put_object(Key=key, Bucket=bucket, Body=obj)


def list_files_in_s3(uri, filetype="tif"):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        objects = paginator.paginate(Bucket=bucket, Prefix=key)
        # Get list of objects if there are any.
        mult_obj = [ob["Contents"] for ob in objects if "Contents" in ob]
        list_obj = []
        for obj in mult_obj:
            ob = [
                "s3://" + bucket + "/" + f["Key"]
                for f in obj
                if f["Key"].endswith(filetype)
            ]
            list_obj = list_obj + ob
        return list_obj


def check_for_squared_pixels(rst):
    if abs(rst.transform[0]) != abs(rst.transform[4]):
        raise PixelsException(f"Pixels are not squared for raster {rst.name}")


def get_bbox_and_footprint_and_stats(
    raster_uri, categorical, bins=None, hist_range=None
):
    """with open(path, "r") as file:
        file.write(json.dumps(catalog_dict))
    Get bounding box and footprint from raster.

    Parameters
    ----------
    raster_uri : str or bytes_io
        The raster file location or bytes_io.
    categorical: boolean, optional
        If True, compute statistics of the pixel data for class weighting.
    bins: int, optional
        Number of bins to use in histogram.
    hist_range: tuple, optional
        Range of histogram.

    Returns
    -------
    bbox : list
        Bounding box of input raster.
    footprint : list
        Footprint of input raster.
    datetime : datetime type
        Datetime from image.
    out_meta : rasterio meta type
        Metadata from raster.
    stats: dict or None
        Statistics of the data, counts by unique value or histogram.
    """
    with rasterio.open(raster_uri) as ds:
        check_for_squared_pixels(ds)
        # Get bounds.
        bounds = ds.bounds
        # Create bbox as list.
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
        # Create bbox as polygon feature.
        footprint = {
            "type": "Polygon",
            "coordinates": [
                [
                    [bounds.left, bounds.bottom],
                    [bounds.left, bounds.top],
                    [bounds.right, bounds.top],
                    [bounds.right, bounds.bottom],
                    [bounds.left, bounds.bottom],
                ]
            ],
        }

        datetime = ds.tags().get("datetime")
        # Compute unique counts if requested.
        stats = None
        img = ds.read()
        if categorical:
            unique_values, unique_counts = np.unique(img, return_counts=True)
            stats = {
                int(key): int(val) for key, val in zip(unique_values, unique_counts)
            }
        else:
            bins = bins or 10
            hist_range = hist_range or (0, 100)
            hist, bin_edges = np.histogram(img, bins=bins, range=hist_range)
            stats = {int(key): int(val) for key, val in zip(hist, bin_edges)}

        return bbox, footprint, datetime, ds.meta, stats
