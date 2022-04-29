import datetime
import io
import json
import os
import zipfile
from collections import Counter

import geopandas as gp
import numpy as np
import pystac
import sentry_sdk
from dateutil import parser
from dateutil.relativedelta import relativedelta
from pystac.validation import STACValidationError
from rasterio.features import bounds

from pixels.exceptions import PixelsException, TrainingDataParseError
from pixels.generator import generator_utils
from pixels.generator.stac_utils import (
    check_file_in_s3,
    get_bbox_and_footprint_and_stats,
    list_files_in_folder,
    save_dictionary,
    upload_files_s3,
)
from pixels.log import logger
from pixels.mosaic import pixel_stack
from pixels.utils import (
    load_dictionary,
    open_file_from_s3,
    run_starmap_multiprocessing,
    timeseries_steps,
    write_raster,
)
from pixels.validators import PixelsConfigValidator


def create_stac_item(
    id_raster,
    footprint,
    bbox,
    datetime,
    out_meta,
    source_path,
    media_type=None,
    additional_links=None,
    out_path=None,
    catalog=None,
):
    if isinstance(datetime, str):
        datetime = parser.parse(datetime)
    # Initiate stac item.
    item = pystac.Item(
        id=id_raster,
        geometry=footprint,
        bbox=bbox,
        datetime=datetime,
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
    if additional_links:
        item.add_link(pystac.Link("corresponding_y", additional_links))
    try:
        # Validate item.
        item.validate()
    except STACValidationError as e:
        logger.warning("Stac Item not validated:", exception=e)
        return None
    if out_path and catalog:
        item.set_self_href(os.path.join(out_path, id_raster, f"{id_raster}.json"))
        item.set_root(catalog)
        item.set_parent(catalog)
        item.make_links_absolute()
        item.make_asset_hrefs_absolute()
        item.save_object()
    return item


def create_stac_item_from_raster(
    path_item,
    source_path,
    data,
    categorical,
    reference_date,
    additional_links,
    catalog,
    out_path=None,
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
        datetime,
        out_meta,
        stats,
    ) = get_bbox_and_footprint_and_stats(raster_file, categorical)

    datetime = datetime or reference_date
    if datetime is None:
        raise TrainingDataParseError("Datetime could not be determined for stac.")

    # Add projection stac extension, assuming input crs has a EPSG id.
    out_meta["proj:epsg"] = out_meta["crs"].to_epsg()
    out_meta["stac_extensions"] = ["projection"]
    # Make transform and crs json serializable.
    out_meta["transform"] = tuple(out_meta["transform"])
    out_meta["crs"] = out_meta["crs"].to_dict()
    out_meta["stats"] = stats
    item = create_stac_item(
        id_raster,
        footprint,
        bbox,
        datetime,
        out_meta,
        path_item,
        media_type=pystac.MediaType.GEOTIFF,
        additional_links=additional_links,
        out_path=out_path,
        catalog=catalog,
    )
    return item, stats


def create_stac_item_from_vector(
    tile, reference_date, source_path, additional_links, out_stac_folder, catalog, crs
):
    if reference_date is None:
        raise TrainingDataParseError("Datetime could not be determined for stac.")

    id_raster = str(tile[0])
    dict_data = gp.GeoSeries(tile[1].geometry).__geo_interface__
    bbox = list(dict_data["bbox"])
    footprint = dict_data["features"][0]["geometry"]
    footprint["coordinates"] = np.array(footprint["coordinates"]).tolist()

    # Add projection stac extension, assuming input crs has a EPSG id.
    out_meta = {
        "proj:epsg": crs.to_epsg(),
        "stac_extensions": ["projection"],
    }
    # Make transform and crs json serializable.
    out_meta["crs"] = {"init": "epsg:" + str(crs.to_epsg())}
    item = create_stac_item(
        id_raster,
        footprint,
        bbox,
        reference_date,
        out_meta,
        source_path,
        media_type=pystac.MediaType.GEOJSON,
        additional_links=additional_links,
        out_path=out_stac_folder,
        catalog=catalog,
    )

    return item


def parse_prediction_area(
    source_path,
    save_files=False,
    description="",
    reference_date=None,
    additional_links=None,
):
    """
    From a geojson build a stac catalog.

    If a "datetime" tag is found in the metadata of the rasters, that value is
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
        additional_links : str, href
            Additional links to other catalogs.

    Returns
    -------
        catalog : dict
            Stac catalog dictionary containing all the raster items.
    """

    if source_path.startswith("s3"):
        data = open_file_from_s3(source_path)
        data = data["Body"]
    else:
        data = source_path
    try:
        tiles = gp.read_file(data)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise PixelsException(f"Error in reading from shapefile: {e}")
    file_format = source_path.split(".")[-1]
    id_name = os.path.split(source_path)[-1].replace(f".{file_format}", "")
    catalog = pystac.Catalog(id=id_name, description=description)
    # For every tile geojson file create an item, add it to catalog.
    out_stac_folder = os.path.join(os.path.dirname(source_path), "stac")
    catalog.normalize_hrefs(out_stac_folder)
    result_parse = run_starmap_multiprocessing(
        create_stac_item_from_vector,
        tiles.iterrows(),
        [
            reference_date,
            source_path,
            additional_links,
            out_stac_folder,
            catalog,
            tiles.crs,
        ],
        iterator_size=len(tiles),
    )
    catalog.add_items(result_parse)
    # Normalize paths inside catalog.
    if additional_links:
        catalog.add_link(pystac.Link("corresponding_y", additional_links))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()
    # Save files if bool is set.
    if save_files:
        catalog.save_object()
    return catalog


def parse_training_data(
    source_path,
    categorical,
    save_files=False,
    description="",
    reference_date=None,
    additional_links=None,
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
        additional_links : str, href
            Additional links to other catalogs.

    Returns
    -------
        catalog : dict
            Stac catalog dictionary containing all the raster items.
    """
    logger.debug(f"Building stac catalog for {source_path}.")
    data = None
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
            additional_links=additional_links,
        )
    if source_path.endswith(".zip"):
        # parse_collections_rasters
        if source_path.startswith("s3"):
            data = generator_utils.open_object_from_s3(source_path)
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
        raster_list = list_files_in_folder(source_path + "/", filetype="tif")
        out_path = source_path
    catalog = pystac.Catalog(id=id_name, description=description)
    logger.debug(f"Found {len(raster_list)} source rasters.")
    # For every raster in the zip file create an item, add it to catalog.
    global_stats = Counter()
    # Parse the raster data images in parallel.
    out_stac_folder = os.path.join(out_path, "stac")
    catalog.normalize_hrefs(out_stac_folder)
    result_parse = run_starmap_multiprocessing(
        create_stac_item_from_raster,
        raster_list,
        [
            source_path,
            data,
            categorical,
            reference_date,
            additional_links,
            catalog,
            out_stac_folder,
        ],
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
    if additional_links:
        catalog.add_link(pystac.Link("corresponding_y", additional_links))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()
    # Save files if bool is set.
    if save_files:
        catalog.save_object()
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
    geojson["bbox"] = bounds(geojson)
    return geojson


def prepare_pixels_config(
    item,
    config,
):
    """
    Based on an item build a config file to use on pixels.

    Parameters
    ----------
        item : pystac item type
            Item representing one raster.
        config : dict
            Pixels configuration dict to validate. It will be validated through the
            PixelsConfigValidator class.
    Returns
    -------
        config : dict
            Dictionary containing the parameters to pass on to pixels.
    """
    # Compute geojson from item.
    if item is str:
        item = pystac.read_file(item)
    config["geojson"] = build_geometry_geojson(item)

    # Validate data.
    validator = PixelsConfigValidator(**config)
    config = validator.dict()

    # If requested, use a fixed time range starting from the individual item
    # datestamps.
    dynamic_dates_interval = config.pop("dynamic_dates_interval")
    dynamic_dates_step = config.pop("dynamic_dates_step")
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
        config["end"] = end.isoformat()
        config["start"] = start.isoformat()
    elif not config.get("end"):
        # If no end data is specified, use the date from the stac item.
        config["end"] = item.datetime.date().isoformat()

    return config


def create_time_bubbles(timesteps, timesteps_not_available):
    """
    Creates joining groups of timesteps. It assumes that both inputs
    are ordered by time.

    Parameters
    ----------
        timesteps : List of datetime.date
            List of timeranges to be collected.
        timesteps_not_available : List of datetime.date
            List of timeranges not collected.
    Returns
    -------
        bubbles : list of timeranges
            List of groups of joining timesteps_not_available.

    """
    bubbles = []
    bubble = []
    for timestep in timesteps:
        if timestep in timesteps_not_available:
            bubble.append(timestep)
        elif len(bubble) > 0:
            bubbles.append(bubble)
            bubble = []
    if len(bubble) > 0:
        bubbles.append(bubble)
    return bubbles


def existing_timesteps_range(timesteps, existing_files):
    """
    Checks the from already download images which asked timesteps are not
    yet downloaded.

    Parameters
    ----------
        timesteps : List of datetime.date
            List of timeranges to be collected.
        existing_files : List of datetime.date
            List of dates already collected.
    Returns
    -------
        start : str
            Collecting start date.
        end : str
            Collecting end date.
    """
    existing_files = [os.path.basename(f).replace(".tif", "") for f in existing_files]
    list_dates = [datetime.datetime.strptime(f, "%Y_%m_%d") for f in existing_files]
    list_dates = [f.date() for f in list_dates]
    timesteps = list(timesteps)
    start = str(min(min(timesteps)))
    end = str(max(max(timesteps)))
    # Assumption! if there is more dates in the images then the collection should be complete.
    if len(list_dates) != 0:
        timesteps_not_available = []
        for timerange in timesteps:
            check = False
            for date in list_dates:
                if timerange[0] <= date <= timerange[1]:
                    check = True
                    list_dates.remove(date)
            if not check:
                timesteps_not_available.append(timerange)
        if len(timesteps) > len(timesteps_not_available):
            time_bubbles = create_time_bubbles(timesteps, timesteps_not_available)
        if len(time_bubbles) == 1:
            start = str(min(min(timesteps_not_available)))
            end = str(max(max(timesteps_not_available)))
        elif len(time_bubbles) == 0:
            return None, None
        else:
            start = [min(f[0]) for f in time_bubbles]
            end = [max(f[-1]) for f in time_bubbles]
    return start, end


def get_and_write_raster_from_item(
    item, x_folder, input_config, discrete_training=True, overwrite=False
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
            Catalog containing the collected info.
    """
    # Build a complete configuration json for pixels.
    config = prepare_pixels_config(item, input_config)
    out_path = os.path.join(x_folder, "data", f"pixels_{str(item.id)}")
    # Check if all the timesteps have images already
    if not overwrite:
        # Timestep is a range of dates to build each image.
        timesteps = timeseries_steps(
            config["start"],
            config["end"],
            config["interval"],
            interval_step=config["interval_step"],
        )
        # List all images already downloaded.
        existing_files = list_files_in_folder(out_path + "/", filetype="tif")
        start, end = existing_timesteps_range(timesteps, existing_files)
        if start is None:
            logger.warning(f"All timesteps already downloaded for {str(item.id)}")
            return
        if isinstance(start, str):
            config["start"] = start
            config["end"] = end
            meta, dates, results = pixel_stack(**config)
        else:
            dates = []
            results = []
            meta = None
            for st, en in zip(start, end):
                config["start"] = st
                config["end"] = en
                output_meta, date, result = pixel_stack(**config)
                if isinstance(output_meta, dict):
                    meta = output_meta
                if date is not None:
                    dates.append(date)
                    results.append(result)
            if dates:
                dates = np.concatenate(dates).tolist()
                results = np.concatenate(results)
    else:
        # Run pixels and get the dates, the images (as numpy) and the raster meta.
        meta, dates, results = pixel_stack(**config)
    if not dates or meta is None:
        logger.warning(f"No images for {str(item.id)}")
        return
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
    x_cat = parse_training_data(
        out_path, False, save_files=True, additional_links=item.get_self_href()
    )

    # Build an intermediate index catalog for the full one.
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
    additional_links="",
):
    """
    From a path containing pystac items build a pystac catalog.

    Parameters
    ----------
        path_to_items : str
            Path to items.
        filetype : str, optional
        id_name : str, optional
        description : str, optional
        additional_links : str, optional

    Returns
    -------
        catalog : pystac catalog
    """
    items_list = list_files_in_folder(path_to_items, filetype="_item.json")
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
    if additional_links:
        catalog.add_link(pystac.Link("corresponding_source", additional_links))
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
    additional_links=None,
):
    """
    From a list of catalogs build a pystac collection.

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
    if additional_links:
        collection.add_link(pystac.Link("origin_files", additional_links))
    collection.make_all_links_absolute()
    # collection.normalize_hrefs(path_to_pixels)
    # collection.validate_all()
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
            File or dictionary containing the pixels configuration.
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
    # Remove geojson attribute from configuration.
    if "geojson" in input_config:
        input_config.pop("geojson")
    overwrite = input_config.pop("overwrite", False)
    # If there is no images in the collection set overwrite to True.
    out_folder = os.path.join(x_folder, "data")
    list_files = list_files_in_folder(out_folder, filetype=".tif")
    if len(list_files) == 0:
        overwrite = True
    # Batch environment variables.
    array_index = int(os.getenv("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    # Read the catalog.
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
                get_and_write_raster_from_item(
                    item, x_folder, input_config, overwrite=overwrite
                )
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.warning(
                    f"Error in collect_from_catalog_subsection. Running get_and_write_raster_from_item: {e}"
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
    catalogs_path_list = list_files_in_folder(downloads_folder, filetype="catalog.json")
    list_cats = list_files_in_folder(
        downloads_folder, filetype="timerange_images_index.json"
    )
    if not list_cats:
        raise PixelsException(f"Trying to build an empty catalog from {x_folder}")

    # Open all index catalogs and merge them.
    index_catalog = {}
    for cat in list_cats:
        cat_dict = load_dictionary(cat)
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
        additional_links=source_path,
    )


def collect_from_catalog(y_catalog, config_file, additional_links=None):
    """
    From a catalog containing the Y training data and a pixels configuration
    file collect pixels and build X collection stac.

    Parameters
    ----------
        y_catalog : pystac catalog
            Catalog with the information where to download data.
        config_file : dict or path to json file
            File or dictionary containing the pixels configuration.
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
    # Remove geojson attribute from configuration.
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
        additional_links=additional_links,
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
            File or dictionary containing the pixels configuration.
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
        y_catalog, config_file, additional_links=source_path
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
        # Read old collection, merge them together
        existing_collection = pystac.Catalog.from_file(existing_collection_path)
        for child in existing_collection.get_children():
            if child not in final_collection.get_children():
                final_collection.add_child(child)
    final_collection.update_extent_from_items()
    final_collection.make_all_asset_hrefs_absolute()
    final_collection.make_all_links_absolute()
    final_collection.save_object(pystac.CatalogType.ABSOLUTE_PUBLISHED)
    return final_collection
