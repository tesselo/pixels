import glob
import io
import json
import logging
import os
import shutil
import zipfile
from urllib.parse import urlparse

import boto3
import numpy as np
import pystac
import rasterio
from dateutil import parser
from pystac import STAC_IO

from pixels.const import (
    PIXELS_COMPOSITE_MODE,
    PIXELS_LATEST_PIXEL_MODE,
    PIXELS_MODES,
    PIXELS_S2_STACK_MODE,
    TESSELO_TAG_NAMESPACE,
)
from pixels.exceptions import PixelsException, TrainingDataParseError
from pixels.mosaic import composite, latest_pixel, latest_pixel_s2_stack
from pixels.utils import write_raster

# Get logger

logger = logging.getLogger(__name__)


def get_bbox_and_footprint(raster_uri):
    """
    Get bounding box and footprint from raster.

    Parameters
    ----------
    raster_uri : str or bytes_io
        The raster file location or bytes_io.

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
    """
    with rasterio.open(raster_uri) as ds:
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
        datetime_var = ds.tags(ns=TESSELO_TAG_NAMESPACE).get("datetime")
        return bbox, footprint, datetime_var, ds.meta


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


def open_file_from_s3(source_path):
    s3_path = source_path.split("s3://")[1]
    bucket = s3_path.split("/")[0]
    path = s3_path.replace(bucket + "/", "")
    s3 = boto3.client("s3")
    data = s3.get_object(Bucket=bucket, Key=path)
    return data


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


def upload_obj_s3(uri, obj):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.client("s3")
        s3.put_object(Key=key, Bucket=bucket, Body=obj)


def upload_files_s3(path, file_type=".json"):
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
    shutil.rmtree(sta)


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


def list_files_in_s3(uri, filetype="tif"):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        theObjs = paginator.paginate(Bucket=bucket, Prefix=key)
        mult_obj = [ob["Contents"] for ob in theObjs]
        list_obj = []
        for obj in mult_obj:
            ob = [
                "s3://" + bucket + "/" + f["Key"]
                for f in obj
                if f["Key"].endswith(filetype)
            ]
            list_obj = list_obj + ob
    return list_obj


def stac_s3_write_method(uri, txt):
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path[1:]
        s3 = boto3.resource("s3")
        s3.Object(bucket, key).put(Body=txt)
    else:
        STAC_IO.default_write_text_method(uri, txt)


def get_catalog_length(catalog_path):
    if catalog_path.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
    catalog = pystac.Catalog.from_file(catalog_path)
    size = len(catalog.get_item_links())
    return size


def parse_prediction_area(
    source_path,
    save_files=False,
    description="",
    reference_date=None,
    aditional_links=None,
):
    """
    From a geojson build a stac catalog.

    If a "datetime" tag is found in the metadata of the rastes, that value is
    extracted and passed as date to the catalog items.

    Parameters
    ----------
        source_path : str
            Path to the zip file or folder containing the rasters.
        save_files : bool, optional
            Set True to save files from catalog and items.
        description : str, optional
            Description to be used in the catalog.
        reference_date : str, optional
            Date or datetime string. Used as the date on catalog items if not
            found in the input files.
        aditional_links : str, href
            Aditionl links to other catalogs.

    Returns
    -------
        catalog : dict
            Stac catalog dictionary containing all the raster items.
    """
    import geopandas as gp

    try:
        tiles = gp.read_file(source_path)
    except Exception as E:
        if source_path.startswith("s3"):
            STAC_IO.read_text_method = stac_s3_read_method
            STAC_IO.write_text_method = stac_s3_write_method
            data = open_file_from_s3(source_path)
            tiles = gp.read_file(data["Body"])
        else:
            logger.warning(f"Error in parse_prediction_area: {E}")

    id_name = os.path.split(source_path)[-1].replace(".geojson", "")
    catalog = pystac.Catalog(id=id_name, description=description)
    # For every tile geojson file create an item, add it to catalog.
    size = len(tiles)
    for count in range(size):
        tile = tiles.iloc[count : count + 1]
        id_raster = str(tile.index.to_list()[0])
        string_data = tile.geometry.to_json()
        dict_data = json.loads(string_data)
        bbox = dict_data["bbox"]
        footprint = dict_data["features"][0]["geometry"]
        datetime_var = None
        # Ensure datetime var is set properly.
        if datetime_var is None:
            if reference_date is None:
                raise TrainingDataParseError(
                    "Datetime could not be determined for stac."
                )
            else:
                datetime_var = reference_date
        # Ensure datetime is object not string.
        datetime_var = parser.parse(datetime_var)
        out_meta = {}
        # Add projection stac extension, assuming input crs has a EPSG id.
        out_meta["proj:epsg"] = tile.crs.to_epsg()
        out_meta["stac_extensions"] = ["projection"]
        # Make transform and crs json serializable.
        out_meta["crs"] = {"init": "epsg:" + str(tile.crs.to_epsg())}
        # Create stac item.
        item = pystac.Item(
            id=id_raster,
            geometry=footprint,
            bbox=bbox,
            datetime=datetime_var,
            properties=out_meta,
        )
        # Register raster as asset of item.
        item.add_asset(
            key=id_raster,
            asset=pystac.Asset(
                href=source_path,
                media_type=pystac.MediaType.GEOJSON,
            ),
        )
        if aditional_links:
            item.add_link(pystac.Link("corresponding_y", aditional_links))
        # Validate item.
        item.validate()
        # Add item to catalog.
        catalog.add_item(item)
    # Normalize paths inside catalog.
    if aditional_links:
        catalog.add_link(pystac.Link("corresponding_y", aditional_links))
    catalog.normalize_hrefs(os.path.join(os.path.dirname(source_path), "stac"))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()
    # catalog.validate_all()
    # Save files if bool is set.
    if save_files:
        catalog.save(catalog_type=pystac.CatalogType.ABSOLUTE_PUBLISHED)
    return catalog


def parse_training_data(
    source_path,
    save_files=False,
    description="",
    reference_date=None,
    aditional_links=None,
):
    """
    From a zip files of rasters or a folder build a stac catalog.

    If a "datetime" tag is found in the metadata of the rastes, that value is
    extracted and passed as date to the catalog items.

    Parameters
    ----------
        source_path : str
            Path to the zip file or folder containing the rasters.
        save_files : bool, optional
            Set True to save files from catalog and items.
        description : str, optional
            Description to be used in the catalog.
        reference_date : str, optional
            Date or datetime string. Used as the date on catalog items if not
            found in the input files.
        aditional_links : str, href
            Aditionl links to other catalogs.

    Returns
    -------
        catalog : dict
            Stac catalog dictionary containing all the raster items.
    """
    logger.debug("Building stac catalog for {}.".format(source_path))
    if source_path.endswith("geojson"):
        return parse_prediction_area(
            source_path,
            save_files=save_files,
            description=description,
            reference_date=reference_date,
            aditional_links=aditional_links,
        )
    if source_path.endswith(".zip"):
        if source_path.startswith("s3"):
            data = open_zip_from_s3(source_path)
            STAC_IO.read_text_method = stac_s3_read_method
            STAC_IO.write_text_method = stac_s3_write_method
        else:
            data = source_path
        # Open zip file.
        archive = zipfile.ZipFile(data, "r")
        # Create stac catalog.
        id_name = os.path.split(os.path.dirname(source_path))[-1]
        raster_list = []
        for af in archive.filelist:
            if af.filename.endswith(".tif"):
                raster_list.append(af.filename)
        out_path = os.path.dirname(source_path)
    else:
        id_name = os.path.split(source_path)[-1]
        if source_path.startswith("s3"):
            STAC_IO.read_text_method = stac_s3_read_method
            STAC_IO.write_text_method = stac_s3_write_method
            raster_list = list_files_in_s3(source_path + "/", filetype="tif")
        else:
            raster_list = glob.glob(source_path + "/*.tif", recursive=True)
        out_path = source_path
    catalog = pystac.Catalog(id=id_name, description=description)
    logger.debug("Found {} source rasters.".format(len(raster_list)))
    # For every raster in the zip file create an item, add it to catalog.
    for path_item in raster_list:
        id_raster = os.path.split(path_item)[-1].replace(".tif", "")
        raster_file = path_item
        # For zip files, wrap the path with a zip prefix.
        if source_path.endswith(".zip") and source_path.startswith("s3"):
            file_in_zip = zipfile.ZipFile(data, "r")
            raster_file = file_in_zip.read(path_item)
            raster_file = io.BytesIO(raster_file)
            path_item = "zip://{}!/{}".format(source_path, path_item)
        elif source_path.endswith(".zip"):
            path_item = "zip://{}!/{}".format(source_path, path_item)
            raster_file = path_item
        # Extract metadata from raster.
        bbox, footprint, datetime_var, out_meta = get_bbox_and_footprint(raster_file)

        # Ensure datetime var is set properly.
        if datetime_var is None:
            if reference_date is None:
                raise TrainingDataParseError(
                    "Datetime could not be determined for stac."
                )
            else:
                datetime_var = reference_date
        # Ensure datetime is object not string.
        datetime_var = parser.parse(datetime_var)
        # Add projection stac extension, assuming input crs has a EPSG id.
        out_meta["proj:epsg"] = out_meta["crs"].to_epsg()
        out_meta["stac_extensions"] = ["projection"]
        # Make transform and crs json serializable.
        out_meta["transform"] = tuple(out_meta["transform"])
        out_meta["crs"] = out_meta["crs"].to_dict()
        # out_meta["crs"] = out_meta["crs"].to_epsg()
        # Create stac item.
        item = pystac.Item(
            id=id_raster,
            geometry=footprint,
            bbox=bbox,
            datetime=datetime_var,
            properties=out_meta,
        )
        # Register raster as asset of item.
        item.add_asset(
            key=id_raster,
            asset=pystac.Asset(
                href=path_item,
                media_type=pystac.MediaType.GEOTIFF,
            ),
        )
        if aditional_links:
            item.add_link(pystac.Link("corresponding_y", aditional_links))
        # Validate item.
        item.validate()
        # Add item to catalog.
        catalog.add_item(item)
    # Normalize paths inside catalog.
    if aditional_links:
        catalog.add_link(pystac.Link("corresponding_y", aditional_links))
    catalog.normalize_hrefs(os.path.join(out_path, "stac"))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()
    # catalog.validate_all()
    # Save files if bool is set.
    if save_files:
        catalog.save(catalog_type=pystac.CatalogType.ABSOLUTE_PUBLISHED)
    return catalog


def build_geometry_geojson(item):
    """
    Build GeoJson from item bounding box.

    Parameters
    ----------
        item : pystac item type
            Item representing one raster.
    Returns
    -------
        geojson: dict
            Dictionary containing the bounding box from input raster.
    """
    coords = item.geometry["coordinates"]
    if len(np.array(coords).shape) != 3:
        coords = coords[0][:1]
    geojson = {
        "type": "FeatureCollection",
        "crs": {"init": "EPSG:" + str(item.properties["proj:epsg"])},
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords,
                },
            },
        ],
    }
    return geojson


def validate_pixels_config(
    item,
    start="2020-01-01",
    end=None,
    interval="all",
    scale=10,
    clip=True,
    bands=("B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"),
    maxcloud=20,
    pool_size=0,
):
    """
    Based on a item build a config file to use on pixels.

    Parameters
    ----------
        item : pystac item type
            Item representing one raster.
        start : str, optional
            Date to start search on pixels.
        end : str, optional
            Date to end search on pixels.
        interval : str, optional
        scale : int, optional
        clip : boolean, optional
        bands : tuple, optional
        maxcloud: int, optional
            Maximun accepted cloud coverage in image.
        pool_size: int, optional
    Returns
    -------
        config : dict
            Dictionary containing the parameters to pass on to pixels.
    """
    if item is str:
        item = pystac.read_file(item)
    geojson = build_geometry_geojson(item)
    # If no end data is specify, fetch from item. Datetime to format 'YYYY-MM-DD'
    if not end:
        end = item.datetime.isoformat()[:10]

    config = {
        "geojson": geojson,
        "start": start,
        "end": end,
        "interval": interval,
        "scale": scale,
        "clip": clip,
        "bands": bands,
        "maxcloud": maxcloud,
        "pool_size": pool_size,
    }
    return config


def run_pixels(config, mode="s2_stack"):
    """
    Run pixels, based on a config file and a chosen mode.

    Parameters
    ----------
        config : dict
            Dictionary containing the parameters to pass on to pixels.
        mode : str, optional
            Mode to use pixel. Avaible modes:
                's2_stack' : All avaible timesteps in timerange. -> latest_pixel_s2_stack()
                'latest': Lastest avaible scene in timerange. -> latest_pixel()
                'composite' Composite from best pixels in timerange. -> composite()
    Returns
    -------
        dates : list
            List of string containing the dates.
        results : list
            List of arrays containing the images.
        meta_data : dict
            Dictionary containing the item's meta data.
    """
    if mode == PIXELS_S2_STACK_MODE:
        result = latest_pixel_s2_stack(**config)
    elif mode == PIXELS_LATEST_PIXEL_MODE:
        result = latest_pixel(**config)
    elif mode == PIXELS_COMPOSITE_MODE:
        result = composite(**config)
    else:
        raise ValueError(
            "Found invalid pixel mode {}. Avaible modes: {}.".format(
                mode, ", ".join(PIXELS_MODES)
            )
        )

    return result


def get_and_write_raster_from_item(item, x_folder, input_config):
    """
    Based on a pystac item get the images in timerange from item's bbox.
    Write them as a raster afterwards. Builds catalog from collected data.

    Parameters
    ----------
        item : pystac item type
            Item representing one raster.
        input_config : dict
            Possible parameters for config json.
    Returns
    -------
        x_cat : str
            Catalog containg the collected info.
    """
    # Build a configuration json for pixels.
    config = validate_pixels_config(item, **input_config)
    # Run pixels and get the dates, the images (as numpy) and the raster meta.
    meta, dates, results = run_pixels(config)
    if not meta:
        logger.info(f"No images for {item.id}")
        return
    # For a lack of out_path argument build one based on item name.
    # The directory for the raster will be one folder paralel to the stac one
    # called pixels.
    out_path = os.path.join(x_folder, "data", f"pixels_{str(item.id)}")
    out_paths_tmp = []
    # Iterate over every timestep.
    for date, np_img in zip(dates, results):
        # If the given image is empty continue to next.
        if not np_img.shape:
            continue
        # Save raster to machine or s3
        out_path_date = os.path.join(out_path, date.replace("-", "_") + ".tif")
        if out_path_date.startswith("s3"):
            out_path_date = out_path_date.replace("s3://", "tmp/")
            out_paths_tmp.append(out_path_date)
        if not os.path.exists(os.path.dirname(out_path_date)):
            os.makedirs(os.path.dirname(out_path_date))
        write_raster(np_img, meta, out_path=out_path_date, tags={"datetime": date})
    if out_path.startswith("s3"):
        upload_files_s3(os.path.dirname(out_paths_tmp[0]), file_type="tif")
    try:
        x_cat = parse_training_data(
            out_path, save_files=True, aditional_links=item.get_self_href()
        )
    except Exception as E:
        logger.warning(f"Error in get_and_write_raster_from_item: {E}")
    return x_cat


def build_collection_from_pixels(
    catalogs,
    path_to_pixels="",
    collection_id="",
    collection_title="",
    collection_description="",
    save_files=False,
    aditional_links=None,
):
    """
    From a list of catalogs build a pystact collection.

    Parameters
    ----------
        catalogs : list of pystac catalogs
            List of catalogs to include in the collection.
        path_to_pixels : str, optional
            Output path for the collection json file.
        collection_id : str, optional
        collection_title : str, optional
        collection_description : str, optional
        save_files : bool, optional
            Set True to save files from catalog and items.

    Returns
    -------
        collection : pystac collection
    """
    if not path_to_pixels:
        path_to_pixels = os.path.split(os.path.dirname(catalogs[0].get_self_href()))[0]

    spatial_extent = pystac.SpatialExtent([[]])
    temporal_extent = pystac.TemporalExtent([[None, None]])
    collection_extent = pystac.Extent(spatial_extent, temporal_extent)

    collection = pystac.Collection(
        id=collection_id,
        title=collection_title,
        description=collection_description,
        extent=collection_extent,
    )
    collection.add_children(catalogs)
    collection.update_extent_from_items()
    collection.set_self_href(path_to_pixels + "/collection.json")
    collection.make_all_asset_hrefs_absolute()
    if aditional_links:
        collection.add_link(pystac.Link("origin_files", aditional_links))
    collection.make_all_links_absolute()
    # collection.normalize_hrefs(path_to_pixels)
    # collection.validate_all()
    if path_to_pixels.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
    if save_files:
        collection.save(pystac.CatalogType.ABSOLUTE_PUBLISHED)
    return collection


def collect_from_catalog_subsection(y_catalog_path, config_file, items_per_job):
    """
    From a catalog containing the Y training data and a pixels configuration
    file collect pixels and build X collection stac.

    Parameters
    ----------
        y_catalog_path : pystac catalog path
            Catalog with the information where to download data.
        config_file : path to json file
            File or dictonary containing the pixels configuration.
        items_per_job : int
            Number of items per jobs.
    """
    # Open config file and load as dict.
    if config_file.startswith("s3"):
        json_data = open_file_from_s3(config_file)["Body"].read()
        if isinstance(json_data, bytes):
            json_data = json_data.decode("utf-8")
        input_config = json.loads(json_data)
    else:
        f = open(config_file)
        input_config = json.load(f)
    x_folder = os.path.dirname(config_file)
    # Remove geojson atribute from configuration.
    if "geojson" in input_config:
        input_config.pop("geojson")
    # Batch enviroment variables.
    array_index = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    # Read the catalog.
    if y_catalog_path.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
    y_catalog = pystac.Catalog.from_file(y_catalog_path)
    # Get the list of index for this batch.
    item_list = [
        *range(array_index * int(items_per_job), (array_index + 1) * int(items_per_job))
    ]
    count = 0
    check = False
    for item in y_catalog.get_all_items():
        if count in item_list:
            check = True
            try:
                get_and_write_raster_from_item(item, x_folder, input_config)
            except Exception as E:
                logger.warning(f"Error in collect_from_catalog_subsection: {E}")
        elif check is True:
            break
        count = count + 1


def create_x_catalog(x_folder, source_path=None):
    """
    From a folder containg the X catalogs build the collection.

    Parameters
    ----------
        x_folder : str
            Config root path, path to build collection.
        source_path : str
            Path to source zip file or folder (Y input).
    """
    # Build a stac collection from all downloaded data.
    downloads_folder = os.path.join(x_folder, "data")
    x_catalogs = []
    if x_folder.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
    catalogs_path_list = list_files_in_s3(downloads_folder, filetype="catalog.json")
    for cat_path in catalogs_path_list:
        x_cat = pystac.Catalog.from_file(cat_path)
        x_catalogs.append(x_cat)
    build_collection_from_pixels(
        x_catalogs,
        save_files=True,
        collection_id="x_collection_"
        + os.path.split(os.path.dirname(downloads_folder))[-1],
        path_to_pixels=downloads_folder,
        aditional_links=source_path,
    )


def collect_from_catalog(y_catalog, config_file, aditional_links=None):
    """
    From a catalog containing the Y training data and a pixels configuration
    file collect pixels and build X collection stac.

    Parameters
    ----------
        y_catalog : pystac catalog
            Catalog with the information where to download data.
        config_file : dict or path to json file
            File or dictonary containing the pixels configuration.
    Returns
    -------
        x_collection : pystac collection
            Pystac collection with all the metadata.
    """
    # Open config file and load as dict.
    if config_file.startswith("s3"):
        json_data = open_file_from_s3(config_file)["Body"].read()
        if isinstance(json_data, bytes):
            json_data = json_data.decode("utf-8")
        input_config = json.loads(json_data)
    else:
        f = open(config_file)
        input_config = json.load(f)
    x_folder = os.path.dirname(config_file)
    # Remove geojson atribute from configuration.
    if "geojson" in input_config:
        input_config.pop("geojson")
    # Iterate over every item in the input data, run pixels and save results to
    # rasters.
    x_catalogs = []
    count = 0
    for item in y_catalog.get_all_items():
        logger.info(
            f"Collecting item: {item.id} and writing rasters. Currently at {round(count / (len(y_catalog.get_item_links())) * 100, 2)}%"
        )
        count = count + 1
        try:
            x_catalogs.append(
                get_and_write_raster_from_item(item, x_folder, input_config)
            )
        except Exception as E:
            logger.warning(f"Error in get_and_write_raster_from_item: {E}")
            continue
    # Build a stac collection from all downloaded data.
    downloads_folder = os.path.join(x_folder, "data")
    x_collection = build_collection_from_pixels(
        x_catalogs,
        save_files=True,
        collection_id=f"x_collection_{os.path.split(os.path.dirname(downloads_folder))[-1]}",
        path_to_pixels=downloads_folder,
        aditional_links=aditional_links,
    )

    return x_collection


def create_and_collect(source_path, config_file):
    """
    From a zip file containing the Y training data and a pixels configuration
    file collect pixels and build stac item.
    TODO: Add better descriptions to catalogs and collections.

    Parameters
    ----------
        source_path : str
            Path to zip file or folder containing rasters.
        config_file : dict or path to json file
            File or dictonary containing the pixels configuration.
    Returns
    -------
        final_collection : pystac collection
            Pystac collection with all the metadata.
    """
    # Build stac catalog from input data.
    logger.info("Building stac files for input data.")
    y_catalog = parse_training_data(
        source_path, save_files=True, reference_date="2020-12-31"
    )
    logger.info("Collecting data using pixels.")
    # Build the X catalogs.
    x_collection = collect_from_catalog(
        y_catalog, config_file, aditional_links=source_path
    )
    # Collection paths
    existing_collection_path = os.path.join(
        os.path.dirname(source_path), "collection.json"
    )
    # Build the final collection containing the X and the Y.
    final_collection = build_collection_from_pixels(
        [x_collection, y_catalog],
        save_files=False,
        collection_id="final",
        path_to_pixels=os.path.dirname(source_path),
    )
    file_check = False
    if existing_collection_path.startswith("s3"):
        file_check = check_file_in_s3(existing_collection_path)
    else:
        file_check = os.path.exists(existing_collection_path)
    if file_check:
        # Read old colection, merge them together
        existing_collection = pystac.Catalog.from_file(existing_collection_path)
        for child in existing_collection.get_children():
            if child not in final_collection.get_children():
                final_collection.add_child(child)
    if source_path.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
    final_collection.update_extent_from_items()
    final_collection.make_all_asset_hrefs_absolute()
    final_collection.make_all_links_absolute()
    final_collection.save_object(pystac.CatalogType.ABSOLUTE_PUBLISHED)
    return final_collection
