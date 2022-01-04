import glob
import io
import json
import os
import zipfile
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pystac
import sentry_sdk
import structlog
from dateutil import parser
from dateutil.relativedelta import relativedelta
from pystac import STAC_IO
from pystac.validation import STACValidationError

from pixels import const
from pixels.exceptions import PixelsException, TrainingDataParseError
from pixels.generator import generator_utils
from pixels.generator.stac_utils import (
    _load_dictionary,
    check_file_in_s3,
    get_bbox_and_footprint_and_stats,
    list_files_in_s3,
    open_file_from_s3,
    save_dictionary,
    stac_s3_read_method,
    stac_s3_write_method,
    upload_files_s3,
)
from pixels.mosaic import pixel_stack
from pixels.utils import write_raster

# Get logger
logger = structlog.get_logger(__name__)


def create_stac_item(
    id_raster,
    footprint,
    bbox,
    datetime_var,
    out_meta,
    source_path,
    media_type=None,
    aditional_links=None,
):
    # Initiate stac item.
    item = pystac.Item(
        id=id_raster,
        geometry=footprint,
        bbox=bbox,
        datetime=datetime_var,
        properties=out_meta,
    )
    # Register kind of asset as asset of item.
    item.add_asset(
        key=id_raster,
        asset=pystac.Asset(
            href=source_path,
            media_type=media_type,
        ),
    )
    if aditional_links:
        item.add_link(pystac.Link("corresponding_y", aditional_links))
    try:
        # Validate item.
        item.validate()
    except STACValidationError:
        return None
    return item


def parse_raster_data_and_create_stac_item(
    path_item, source_path, data, categorical, reference_date, aditional_links
):
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
    (
        bbox,
        footprint,
        datetime_var,
        out_meta,
        stats,
    ) = get_bbox_and_footprint_and_stats(raster_file, categorical)
    # Ensure datetime var is set properly.
    if datetime_var is None:
        if reference_date is None:
            raise TrainingDataParseError("Datetime could not be determined for stac.")
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
    out_meta["stats"] = stats
    # Create stac item.
    item = create_stac_item(
        id_raster,
        footprint,
        bbox,
        datetime_var,
        out_meta,
        path_item,
        media_type=pystac.MediaType.GEOTIFF,
        aditional_links=aditional_links,
    )
    print(item)
    print(stats)
    return item, stats


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

    if source_path.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
        data = open_file_from_s3(source_path)
        data = data["Body"]
    else:
        data = source_path
    try:
        tiles = gp.read_file(data)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.warning(f"Error in reading from shapefile: {e}")
    file_format = source_path.split(".")[-1]
    id_name = os.path.split(source_path)[-1].replace(f".{file_format}", "")
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
        item = create_stac_item(
            id_raster,
            footprint,
            bbox,
            datetime_var,
            out_meta,
            source_path,
            media_type=pystac.MediaType.GEOJSON,
            aditional_links=aditional_links,
        )
        if item:
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
    categorical,
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
        categorical: boolean or str
            If True, the data is considered to be categorical, and statistics
            by class are computed for weighting.  If passed as string, either
            pass "True" or "False".
        save_files : bool or str optional
            Set True to save files from catalog and items. If passed as string,
            either pass "True" or "False".
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

    # If input is string, convert to boolean.
    if isinstance(categorical, str):
        categorical = categorical == "True"
    if isinstance(save_files, str):
        save_files = save_files == "True"

    if source_path.endswith("geojson") or source_path.endswith("gpkg"):
        return parse_prediction_area(
            source_path,
            save_files=save_files,
            description=description,
            reference_date=reference_date,
            aditional_links=aditional_links,
        )
    if source_path.endswith(".zip"):
        # parse_collections_rasters
        if source_path.startswith("s3"):
            data = generator_utils.open_object_from_s3(source_path)
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
    global_stats = Counter()
    # Parse the raster Data images in parallel.
    with Pool(min(len(raster_list), 12)) as p:
        result_parse = p.starmap(
            parse_raster_data_and_create_stac_item,
            zip(
                raster_list,
                [source_path] * len(raster_list),
                [data] * len(raster_list),
                [categorical] * len(raster_list),
                [reference_date] * len(raster_list),
                [aditional_links] * len(raster_list),
            ),
        )
    items = [ite[0] for ite in result_parse]
    stats = [ite[1] for ite in result_parse]
    # Add the list of items to the catalog.
    catalog.add_items(items)
    if categorical:
        # Add item statistics to global stats counter.
        for stat in stats:
            global_stats.update(stat)
        # Store final statistics on catalog.
        # Convert stats to class weights, inversely proportional to their count.
        global_stats_total = sum(global_stats.values())
        global_stats = {
            key: 1 - val / global_stats_total for key, val in global_stats.items()
        }
        # Normalize to sum one.
        global_stats_normalization = sum(global_stats.values())
        global_stats = {
            key: val / global_stats_normalization for key, val in global_stats.items()
        }
        # Store stats as class weights.
        catalog.extra_fields["class_weight"] = global_stats
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


def prepare_pixels_config(
    item,
    start="2020-01-01",
    end=None,
    interval="all",
    interval_step=1,
    scale=10,
    clip=True,
    bands=("B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"),
    maxcloud=20,
    pool_size=0,
    level=None,
    platforms=None,
    limit=None,
    mode="latest_pixel",
    dynamic_dates_interval=None,
    dynamic_dates_step=1,
    discrete_training=True,
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
        interval_step : int, optional
        scale : int, optional
        clip : boolean, optional
        bands : tuple, optional
        maxcloud: int, optional
            Maximun accepted cloud coverage in image.
        pool_size: int, optional
        level : str, optional
            The processing level. Only valid if platforms is S2.
        platform: str or list, optional
            The platforms to use in this collection.
        limit: int, optional
            Limit the number of images per search.
        mode: str, optional
            Mode of pixel collection (all, latest_pixel, or composite).
        dynamic_dates_interval: str, optional
            If provided, the internal item dates are used as end date and this
             interval is applied as the start date.
        dynamic_dates_step: int, optional
            To be used in combination with the dynamic_dates_interval. Defines
            the number of times and interval is applied to go to the start date.
            Defaults to 1.
    Returns
    -------
        config : dict
            Dictionary containing the parameters to pass on to pixels.
    """
    if item is str:
        item = pystac.read_file(item)
    geojson = build_geometry_geojson(item)
    # If requested, use a fixed time range starting from the individual item
    # datestamps.
    if dynamic_dates_interval:
        # Extract the end date from the stac item.
        end = item.datetime.date()
        # Compute the time delta from the dynamic dates configuration.
        delta = relativedelta(
            **{dynamic_dates_interval.lower(): int(dynamic_dates_step)}
        )
        # Set start date as the item end date minus the dynamic date interval.
        start = end - delta
        # Convert both dates to string.
        end = end.isoformat()
        start = start.isoformat()
    elif not end:
        # If no end data is specified, use the date from the stac item.
        end = item.datetime.date().isoformat()
    # Check valid mode.
    if mode not in ["all", "latest_pixel", "composite"]:
        raise PixelsException(f"Latest pixel mode {mode} is not valid.")
    # Ensure platforms is a list. The input can be provided as a single string
    # if only one platform is required.
    if platforms is not None and not isinstance(platforms, (list, tuple)):
        platforms = [platforms]
    # Check if SCL was requested with L1C data.
    if "SCL" in bands and (level != "L2A" or platforms != [const.SENTINEL_2]):
        raise PixelsException(
            f"SCL can only be requested for S2 L2A. Got {platforms} {level}."
        )

    # Create new config dictionary.
    config = {
        "geojson": geojson,
        "start": start,
        "end": end,
        "interval": interval,
        "interval_step": interval_step,
        "scale": scale,
        "clip": clip,
        "bands": bands,
        "maxcloud": maxcloud,
        "pool_size": pool_size,
        "level": level,
        "mode": mode,
        "platforms": platforms,
    }

    if limit is not None:
        config["limit"] = limit

    return config


def get_and_write_raster_from_item(
    item, x_folder, input_config, discrete_training=True
):
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
    # Build a complete configuration json for pixels.
    config = prepare_pixels_config(item, **input_config)
    # Run pixels and get the dates, the images (as numpy) and the raster meta.
    meta, dates, results = pixel_stack(**config)
    if not meta:
        logger.warning(f"No images for {str(item.id)}")
        return
    # For a lack of out_path argument build one based on item name.
    # The directory for the raster will be one folder paralel to the stac one
    # called pixels.
    out_path = os.path.join(x_folder, "data", f"pixels_{str(item.id)}")
    out_paths_tmp = []
    out_paths = []
    # Iterate over every timestep.
    for date, np_img in zip(dates, results):
        # If the given image is empty continue to next.
        if not np_img.shape:
            logger.warning(f"No images for {str(item.id)}")
            continue
        # Save raster to machine or s3
        out_path_date = os.path.join(out_path, date.replace("-", "_") + ".tif")
        out_paths.append(out_path_date)
        if out_path_date.startswith("s3"):
            out_path_date = out_path_date.replace("s3://", "tmp/")
            out_paths_tmp.append(out_path_date)
        if not os.path.exists(os.path.dirname(out_path_date)):
            os.makedirs(os.path.dirname(out_path_date))
        write_raster(
            np_img,
            meta,
            out_path=out_path_date,
            dtype=np_img.dtype,
            tags={"datetime": date},
        )
    if out_path.startswith("s3"):
        upload_files_s3(os.path.dirname(out_paths_tmp[0]), file_type="tif")
    try:
        x_cat = parse_training_data(
            out_path, False, save_files=True, aditional_links=item.get_self_href()
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.warning(f"Error in parsing data in get_and_write_raster_from_item: {e}")
    # Build a intermediate index catalog for the full one.
    stac_catalog_path = str(x_cat.get_self_href())
    # Ensure no duplicates get on the dictionary.
    # Only a temporary solution since this whole pipeline is to change.
    out_paths = list(np.unique(out_paths))
    catalog_dict = {
        f"pixels_id_{str(item.id)}": {
            "x_paths": out_paths,
            "y_path": str(item.assets[item.id].href),
            "stac_catalog": stac_catalog_path,
            "discrete_training": discrete_training,
        }
    }
    # Write file and send to s3.
    save_dictionary(
        os.path.join(
            os.path.dirname(os.path.dirname(stac_catalog_path)),
            "timerange_images_index.json",
        ),
        catalog_dict,
    )

    return x_cat


def build_catalog_from_items(
    path_to_items,
    filetype="_item.json",
    id_name="predictions",
    description="",
    aditional_links="",
):
    """
    From a path containing pystac items build a pystact catalog.

    Parameters
    ----------
        path_to_items : str
            Path to items.
        filetype : str, optional
        id_name : str, optional
        description : str, optional
        aditional_links : str, optional

    Returns
    -------
        catalog : pystac catalog
    """
    if path_to_items.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
        items_list = list_files_in_s3(path_to_items, filetype="_item.json")
    else:
        items_list = glob.glob(f"{path_to_items}/*{filetype}", recursive=True)
    # Abort here if there are no items to create a catalog.
    if not items_list:
        logger.warning(f"No items found to create catalog for {path_to_items}.")
        return
    catalog = pystac.Catalog(id=id_name, description=description)
    for item_path in items_list:
        item = pystac.read_file(item_path)
        # Add item to catalog.
        catalog.add_item(item)
    # Normalize paths inside catalog.
    if aditional_links:
        catalog.add_link(pystac.Link("corresponding_source", aditional_links))
    catalog.set_self_href(os.path.join(os.path.dirname(items_list[0]), "catalog.json"))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()
    catalog.save_object()

    return catalog


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
        license="proprietary",
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
    array_index = int(os.getenv("AWS_BATCH_JOB_ARRAY_INDEX", 0))
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
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.warning(
                    f"Error in collect_from_catalog_subsection. Runing get_and_write_raster_from_item: {e}"
                )
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
    # Build the custom catalog.
    # Build a stac collection from all downloaded data.
    downloads_folder = os.path.join(x_folder, "data")
    x_catalogs = []
    if x_folder.startswith("s3"):
        STAC_IO.read_text_method = stac_s3_read_method
        STAC_IO.write_text_method = stac_s3_write_method
        catalogs_path_list = list_files_in_s3(downloads_folder, filetype="catalog.json")
        list_cats = list_files_in_s3(
            downloads_folder, filetype="timerange_images_index.json"
        )
    else:
        list_cats = glob.glob(
            f"{downloads_folder}/**/timerange_images_index.json", recursive=True
        )
        catalogs_path_list = glob.glob(
            f"{downloads_folder}/**/**/catalog.json", recursive=True
        )

    if not list_cats:
        raise PixelsException(f"Trying to build an empty catalog from {x_folder}")

    # Open all index catalogs and merge them.
    index_catalog = {}
    for cat in list_cats:
        cat_dict = _load_dictionary(cat)
        index_catalog.update(cat_dict)
    # FIXME: it is still unknown if the following line has any effect
    cat_dict["relative_paths"] = False
    cat_path = os.path.join(downloads_folder, "catalogs_dict.json")
    save_dictionary(cat_path, index_catalog)
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
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.warning(f"Error in get_and_write_raster_from_item: {e}")
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
        source_path, False, save_files=True, reference_date="2020-12-31"
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
