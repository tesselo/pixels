import datetime
import os
import zipfile
from collections import Counter
from io import BytesIO

import geopandas as gp
import numpy as np
import pystac
import sentry_sdk
from dateutil import parser
from dateutil.relativedelta import relativedelta
from pystac.validation import STACValidationError
from rasterio.features import bounds

from pixels import tio
from pixels.const import ALLOWED_VECTOR_TYPES
from pixels.exceptions import PixelsException, TrainingDataParseError
from pixels.generator.stac_utils import get_bbox_and_footprint_and_stats
from pixels.log import logger
from pixels.mosaic import pixel_stack
from pixels.utils import run_starmap_multiprocessing, timeseries_steps
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
    crs = out_meta.pop("crs", None)
    # Initiate stac item.
    item = pystac.Item(
        id=id_raster,
        geometry=footprint,
        bbox=bbox,
        datetime=datetime,
        properties=out_meta,
    )
    item.extra_fields["crs"] = crs
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
    item_path,
    source_path,
    archive_data,
    categorical,
    reference_date,
    additional_links,
    catalog,
    out_path=None,
    data_value_range=None,
):
    id_raster = os.path.split(item_path)[-1].replace(".tif", "")

    if tio.is_archive(source_path) and tio.is_remote(source_path):
        file_in_zip = zipfile.ZipFile(archive_data, "r")
        raster_file = file_in_zip.read(item_path)
        raster_file = BytesIO(raster_file)
        item_path = f"zip://{source_path}!/{item_path}"
    elif tio.is_archive(source_path):
        item_path = f"zip://{source_path}!/{item_path}"
        raster_file = item_path
    else:
        raster_file = item_path

    # Extract metadata from raster.
    (bbox, footprint, datetime, out_meta, stats,) = get_bbox_and_footprint_and_stats(
        raster_file, categorical, hist_range=data_value_range
    )
    datetime = datetime or reference_date
    if datetime is None:
        raise TrainingDataParseError("Datetime could not be determined for stac.")

    # Add projection stac extension, assuming input crs has a EPSG id.
    out_meta["proj:epsg"] = out_meta["crs"].to_epsg()
    out_meta["stac_extensions"] = ["projection"]
    # Make transform and crs json serializable.
    out_meta["transform"] = tuple(out_meta["transform"])
    out_meta["crs"] = out_meta["crs"].to_dict()
    out_meta["categorical"] = categorical
    out_meta["value_counts"] = stats
    item = create_stac_item(
        id_raster,
        footprint,
        bbox,
        datetime,
        out_meta,
        item_path,
        media_type=pystac.MediaType.GEOTIFF,
        additional_links=additional_links,
        out_path=out_path,
        catalog=catalog,
    )
    return item, stats


def create_stac_item_from_vector(
    tile,
    reference_date,
    source_path,
    categorical,
    additional_links,
    out_stac_folder,
    catalog,
    crs,
):

    id_raster = str(tile[0])
    dict_data = gp.GeoSeries(tile[1].geometry).__geo_interface__
    bbox = list(dict_data["bbox"])
    footprint = dict_data["features"][0]["geometry"]
    footprint["coordinates"] = np.array(footprint["coordinates"]).tolist()
    reference_date = tile[1].get("date", reference_date)
    klass = tile[1].get("class", None)
    if reference_date is None:
        raise TrainingDataParseError("Datetime could not be determined for stac.")
    # Add projection stac extension, assuming input crs has a EPSG id.
    out_meta = {
        "proj:epsg": crs.to_epsg(),
        "stac_extensions": ["projection"],
    }
    # Make transform and crs json serializable.
    out_meta["crs"] = {"init": "epsg:" + str(crs.to_epsg())}
    out_meta["categorical"] = categorical
    if categorical:
        klass_col_name = "class"
    else:
        klass_col_name = "value"
    out_meta[klass_col_name] = klass
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


def parse_vector_data(
    source_path,
    categorical,
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
            Path to the vector file.
        categorical: boolean
            If True, the data is considered to be categorical, and statistics
            by class are computed for weighting.
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
    data = tio.get(source_path)
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
            categorical,
            additional_links,
            out_stac_folder,
            catalog,
            tiles.crs,
        ],
        iterator_size=len(tiles),
    )
    catalog.add_items(result_parse)
    catalog.extra_fields["type"] = "Catalog"
    catalog.extra_fields["crs"] = {"init": "epsg:" + str(tiles.crs.to_epsg())}
    # Normalize paths inside catalog.
    if additional_links:
        catalog.add_link(pystac.Link("corresponding_y", additional_links))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()

    if save_files:
        catalog.save_object()
    return catalog


def parse_raster_data(
    source_path,
    categorical,
    save_files=False,
    description="",
    reference_date=None,
    additional_links=None,
):
    """
    From a zip files of rasters or a folder build a stac catalog.

    If a "datetime" tag is found in the metadata of the rasters, that value is
    extracted and passed as date to the catalog items.

    Parameters
    ----------
        source_path : str
            Path to the zip file or folder containing the rasters.
        categorical: boolean
            If True, the data is considered to be categorical, and statistics
            by class are computed for weighting.
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

    archive_data = None
    if tio.is_archive(source_path):
        archive_data = tio.get_zippable(source_path)
        archive = zipfile.ZipFile(archive_data, "r")
        # Create stac catalog.
        id_name = os.path.split(os.path.dirname(source_path))[-1]
        raster_list = []
        for file in archive.filelist:
            if file.filename.endswith(".tif"):
                raster_list.append(file.filename)
        out_path = os.path.dirname(source_path)
    else:
        id_name = os.path.split(source_path)[-1]
        raster_list = tio.list_files(source_path, suffix=".tif")
        out_path = source_path
    catalog = pystac.Catalog(id=id_name, description=description)
    logger.debug(f"Found {len(raster_list)} source rasters.")
    # For every raster in the zip file create an item, add it to catalog.
    # Parse the raster data images in parallel.
    out_stac_folder = os.path.join(out_path, "stac")
    catalog.normalize_hrefs(out_stac_folder)
    result_parse = run_starmap_multiprocessing(
        create_stac_item_from_raster,
        raster_list,
        [
            source_path,
            archive_data,
            categorical,
            reference_date,
            additional_links,
            catalog,
            out_stac_folder,
        ],
    )
    items = [ite[0] for ite in result_parse]
    stats = [ite[1] for ite in result_parse]
    # Get nodata value and crs from first item.
    nodata = items[0].properties["nodata"]
    crs = items[0].extra_fields["crs"]
    # Add the list of items to the catalog.
    catalog.add_items(items)
    value_counts = Counter()
    # Add item statistics to global stats counter.
    for stat in stats:
        value_counts.update(stat)
    if nodata is None:
        nodata_count = 0
    else:
        nodata_count = value_counts.pop(int(nodata), 0)
    catalog.extra_fields["values_count"] = value_counts
    catalog.extra_fields["nodata"] = nodata
    catalog.extra_fields["nodata_count"] = nodata_count
    catalog.extra_fields["crs"] = crs
    catalog.extra_fields["categorical"] = categorical
    catalog.extra_fields["type"] = "Catalog"
    if categorical:
        n_samples = sum(value_counts.values())
        n_classes = len(value_counts)
        class_weight_dict = dict()
        # Same method as balanced in scipy class_weights.
        for key in value_counts:
            class_weight = n_samples / (n_classes * value_counts[key])
            class_weight_dict[key] = class_weight
        catalog.extra_fields["class_weight"] = class_weight_dict
    # Normalize paths inside catalog.
    if additional_links:
        catalog.add_link(pystac.Link("corresponding_y", additional_links))
    catalog.make_all_links_absolute()
    catalog.make_all_asset_hrefs_absolute()

    if save_files:
        catalog.save_object()
    return catalog


def is_allowed_vector(source_path):
    source_type = source_path.split(".")[-1]
    return source_type in ALLOWED_VECTOR_TYPES


def is_allowed_raster_container(source_path):
    return tio.is_archive(source_path) or tio.is_dir(source_path)


def parse_data(
    source_path,
    categorical,
    save_files=False,
    description="",
    reference_date=None,
    additional_links=None,
):

    logger.debug(f"Building stac catalog for {source_path}.")

    if isinstance(categorical, str):
        categorical = categorical == "True"
    if isinstance(save_files, str):
        save_files = save_files == "True"

    if is_allowed_vector(source_path):
        return parse_vector_data(
            source_path,
            categorical,
            save_files=save_files,
            description=description,
            reference_date=reference_date,
            additional_links=additional_links,
        )
    elif is_allowed_raster_container(source_path):
        return parse_raster_data(
            source_path,
            categorical,
            save_files=save_files,
            description=description,
            reference_date=reference_date,
            additional_links=additional_links,
        )
    else:
        raise ValueError(
            f"Source path {source_path} is not in an allowed vector format or a container for rasters"
        )


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
    geojson = {
        "type": "FeatureCollection",
        "crs": {"init": "EPSG:" + str(item.properties["proj:epsg"])},
        "features": [
            {
                "type": "Feature",
                "geometry": {**item.geometry},
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
        start : list[str]
            Collecting start date(s).
        end : list[str]
            Collecting end date(s).
    """
    existing_files = [os.path.basename(f).replace(".tif", "") for f in existing_files]
    list_dates = [datetime.datetime.strptime(f, "%Y_%m_%d") for f in existing_files]
    list_dates = [f.date() for f in list_dates]
    timesteps = list(timesteps)
    start = [str(min(min(timesteps)))]
    end = [str(max(max(timesteps)))]
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
            start = [str(min(min(timesteps_not_available)))]
            end = [str(max(max(timesteps_not_available)))]
        elif len(time_bubbles) == 0:
            return None, None
        else:
            start = [str(min(f[0])) for f in time_bubbles]
            end = [str(max(f[-1])) for f in time_bubbles]
    return start, end


def configure_multi_time_bubbles(config, out_path, item, overwrite=False):
    """
    Creates the list of possible configurations to search based on missing images.

    Parameters
    ----------
        config : dict
            Dictionary containing the parameters to pass on to pixels.
        out_path : str
            Path to folder containing the item's images.
        item : pystac item type
            Item representing one raster.
        overwrite : boolen
            Bolean to write all images again.
    Returns
    -------
        configs : list[dict]
            List containing the needed configuration to search.
    """
    if overwrite:
        return [config]
    # Timestep is a range of dates to build each image.
    timesteps = timeseries_steps(
        config["start"],
        config["end"],
        config["interval"],
        interval_step=config["interval_step"],
    )
    existing_files = tio.list_files(out_path, suffix=".tif")
    start, end = existing_timesteps_range(timesteps, existing_files)
    configs = []
    if start is None:
        logger.warning(f"All timesteps already downloaded for {str(item.id)}")
        return
    for st, en in zip(start, end):
        config["start"] = st
        config["end"] = en
        configs.append(config)
    return configs


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
    configs = configure_multi_time_bubbles(config, out_path, item, overwrite)
    if configs is not None:
        # Run pixels.
        for config in configs:
            config["out_path"] = out_path
            pixel_stack(**config)
    out_paths = tio.list_files(f"{out_path}/", suffix=".tif")
    out_paths = list(np.unique(out_paths))
    # Parse data to stac catalogs.
    x_cat = parse_data(
        out_path, False, save_files=True, additional_links=item.get_self_href()
    )
    # Build an intermediate index catalog for the full one.
    stac_catalog_path = str(x_cat.get_self_href())
    # Ensure no duplicates get on the dictionary.
    # Only a temporary solution since this whole pipeline is to change.
    catalog_dict = {
        f"pixels_id_{str(item.id)}": {
            "x_paths": out_paths,
            "y_path": str(item.assets[item.id].href),
            "stac_catalog": stac_catalog_path,
            "discrete_training": discrete_training,
        }
    }

    tio.save_dictionary(
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
    items_list = tio.list_files(path_to_items, suffix="_item.json")
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
    collection.extra_fields["type"] = "Collection"
    collection.extra_fields["crs"] = catalogs[0].extra_fields["crs"]
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
    input_config = tio.load_dictionary(config_file)
    x_folder = os.path.dirname(config_file)
    # Remove geojson attribute from configuration.
    if "geojson" in input_config:
        input_config.pop("geojson")
    overwrite = input_config.pop("overwrite", False)
    # If there is no images in the collection set overwrite to True.
    out_folder = os.path.join(x_folder, "data")
    list_files = tio.list_files(out_folder, suffix=".tif")
    if len(list_files) == 0:
        overwrite = True
    # Batch environment variables.
    array_index = int(os.getenv("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    # Read the catalog.
    y_catalog = pystac.Catalog.from_file(y_catalog_path)
    if y_catalog.catalog_type != pystac.CatalogType.ABSOLUTE_PUBLISHED:
        y_catalog.make_all_links_absolute()
    # Get the list of index for this batch.
    item_indexes = [
        *range(array_index * int(items_per_job), (array_index + 1) * int(items_per_job))
    ]
    catalog_item_links = y_catalog.get_item_links()
    number_of_items = len(catalog_item_links)
    for i in item_indexes:
        if i < number_of_items:
            item_path = catalog_item_links[i].get_href()
            item = pystac.Item.from_file(item_path)
            try:
                get_and_write_raster_from_item(
                    item, x_folder, input_config, overwrite=overwrite
                )
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.warning(
                    f"Error in collect_from_catalog_subsection. Running get_and_write_raster_from_item: {e}"
                )


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
    catalogs_path_list = tio.list_files(downloads_folder, suffix="catalog.json")
    list_cats = tio.list_files(downloads_folder, suffix="timerange_images_index.json")
    if not list_cats:
        raise PixelsException(f"Trying to build an empty catalog from {x_folder}")

    # Open all index catalogs and merge them.
    index_catalog = {}
    for cat in list_cats:
        cat_dict = tio.load_dictionary(cat)
        index_catalog.update(cat_dict)
    cat_path = os.path.join(downloads_folder, "catalogs_dict.json")
    tio.save_dictionary(cat_path, index_catalog)
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
    input_config = tio.load_dictionary(config_file)
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
    y_catalog = parse_data(
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
    if tio.file_exists(existing_collection_path):
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
