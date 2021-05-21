from urllib.parse import urlparse

import boto3
import pystac
import sentry_sdk
from pystac import STAC_IO


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
