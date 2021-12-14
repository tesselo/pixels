import ast
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
import structlog
from pystac import STAC_IO

from pixels.exceptions import PixelsException

logger = structlog.get_logger(__name__)


def stac_s3_write_method(uri, txt):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.resource("s3")
        s3.Object(bucket, key).put(Body=txt)
    else:
        STAC_IO.default_write_text_method(uri, txt)


def stac_s3_read_method(uri):
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
    if catalog_path.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
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


def _load_dictionary(path_file):
    # Open config file and load as dict.
    if path_file.startswith("s3"):
        my_str = open_file_from_s3(path_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        dictionary = json.loads(new_str)
    else:
        with open(path_file, "r") as json_file:
            input_config = json_file.read()
            try:
                dictionary = ast.literal_eval(input_config)
            except:
                dictionary = json.loads(str(input_config))
    return dictionary


def upload_files_s3(path, file_type=".json", delete_folder=True):
    """
    Upload files inside a folder to s3.
    The s3 paths most be the same as the folder.

    Parameters
    ----------
        path : str
            Path to folder containing the files you wan to upload.
        file_type : str, optional
            Filetype to upload, set to json.
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
        return glob.glob(f"{uri}/**{filetype}", recursive=True)


def check_file_in_s3(uri):
    """
    Check if file exists at an S3 uri.

    Parameters
    ----------
    uri: str
        The S3 uri to check if file exists. Example: s3://my-bucket/config.json
    """
    # Split the S3 uri into compoments.
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
    theObjs = s3.list_objects_v2(Bucket=bucket, Prefix=os.path.dirname(key))
    list_obj = [ob["Key"] for ob in theObjs["Contents"]]
    # Ensure key is in list.
    return key in list_obj


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
        theObjs = paginator.paginate(Bucket=bucket, Prefix=key)
        # Get list of objects if thre are any.
        mult_obj = [ob["Contents"] for ob in theObjs if "Contents" in ob]
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


def get_bbox_and_footprint_and_stats(raster_uri, categorical):
    """with open(path, "r") as file:
        file.write(json.dumps(catalog_dict))
    Get bounding box and footprint from raster.

    Parameters
    ----------
    raster_uri : str or bytes_io
        The raster file location or bytes_io.
    categorical: boolean, optional
        If True, compute statistics of the pixel data for class weighting.

    Returns
    -------
    bbox : list
        Bounding box of input raster.
    footprint : list
        Footprint of input raster.
    datetime_var : datetime type
        Datetime from image.
    out_meta : rasterio meta type
        Metadata from raster.
    stats: dict or None
        Statistics of the data, counts by unique value.
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
        # Try getting the datetime in the raster metadata. Set to None if not
        # found.
        datetime_var = ds.tags().get("datetime", None)
        # Compute unique counts if requested.
        stats = None
        if categorical:
            unique_values, uniue_counts = np.unique(ds.read(), return_counts=True)
            stats = {
                int(key): int(val) for key, val in zip(unique_values, uniue_counts)
            }

        return bbox, footprint, datetime_var, ds.meta, stats
