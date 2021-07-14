import ast
import glob
import json
import os
import shutil
from urllib.parse import urlparse

import boto3
import pystac
import sentry_sdk
import structlog
from pystac import STAC_IO

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
    try:
        collection = pystac.Collection.from_file(catalog_path)
        size = len(collection.get_child_links())
    except Exception as e:
        sentry_sdk.capture_exception(e)
        catalog = pystac.Catalog.from_file(catalog_path)
        size = len(catalog.get_item_links())
    return size


def save_dictionary(path, dict):
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
        json.dump(dict, f)
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
        dicti = json.loads(new_str)
    else:
        with open(path_file, "r") as json_file:
            input_config = json_file.read()
            try:
                dicti = ast.literal_eval(input_config)
            except:
                dicti = json.loads(str(input_config))
    return dicti


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
