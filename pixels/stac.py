import glob
import io
import json
import os
import zipfile

import pystac
import rasterio
from dateutil import parser

from pixels.const import (
    PIXELS_COMPOSITE_MODE,
    PIXELS_LATEST_PIXEL_MODE,
    PIXELS_MODES,
    PIXELS_S2_STACK_MODE,
    TESSELO_TAG_NAMESPACE,
)
from pixels.mosaic import composite, latest_pixel, latest_pixel_s2_stack
from pixels.utils import write_raster


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
            "coordinates": (
                (
                    (bounds.left, bounds.bottom),
                    (bounds.left, bounds.top),
                    (bounds.right, bounds.top),
                    (bounds.right, bounds.bottom),
                    (bounds.left, bounds.bottom),
                )
            ),
        }
        # Try getting the datetime in the raster metadata. Set to None if not
        # found.
        datetime_var = ds.tags(ns=TESSELO_TAG_NAMESPACE).get("datetime")
        return bbox, footprint, datetime_var, ds.meta


def parse_training_data(
    zip_path, save_files=False, description="", reference_date=None
):
    """
    From a zip files of rasters or a folder build a stac catalog.

    If a "datetime" tag is found in the metadata of the rastes, that value is
    extracted and passed as date to the catalog items.

    Parameters
    ----------
        zip_path : str
            Path to the zip file or folder containing the rasters.
        save_files : bool, optional
            Set True to save files from catalog and items.
        description : str, optional
            Description to be used in the catalog.
        reference_date : str, optional
            Date or datetime string. Used as the date on catalog items if not
            found in the input files.

    Returns
    -------
        catalog : dict
            Stac catalog dictionary containing all the raster items.
    """
    if zip_path.endswith(".zip"):
        # Open zip file.
        archive = zipfile.ZipFile(zip_path, "r")
        # Create stac catalog.
        id_name = zip_path.replace(os.path.dirname(zip_path), "").replace(".zip", "")
        raster_list = []
        for af in archive.filelist:
            raster_list.append(af.filename)
    else:
        id_name = os.path.split(zip_path)[-1]
        raster_list = glob.glob(zip_path + "*/*.tif", recursive=True)

    catalog = pystac.Catalog(id=id_name, description=description)
    # For every raster in the zip file create an item, add it to catalog.
    for raster in raster_list:
        id_raster = os.path.split(raster)[-1].replace(".tif", "")
        if zip_path.endswith(".zip"):
            img_data = archive.read(raster)
            bytes_io = io.BytesIO(img_data)
            path_item = zip_path + "!/" + raster
        else:
            bytes_io = raster
            path_item = raster
        bbox, footprint, datetime_var, out_meta = get_bbox_and_footprint(bytes_io)
        # Ensure datetime var is set properly.
        if datetime_var is None:
            if reference_date is None:
                raise ValueError("Datetime could not be determined for stac.")
            else:
                datetime_var = reference_date
        # Ensure datetime is object not string.
        datetime_var = parser.parse(datetime_var)
        out_meta["crs"] = out_meta["crs"].to_epsg()
        item = pystac.Item(
            id=id_raster,
            geometry=footprint,
            bbox=bbox,
            datetime=datetime_var,
            properties=out_meta,
        )
        item.add_asset(
            key=id_raster,
            asset=pystac.Asset(
                href=path_item,
                media_type=pystac.MediaType.GEOTIFF,
            ),
        )
        crs = out_meta["crs"]
        pystac.extensions.projection.ProjectionItemExt(item).apply(crs)
        # item.validate()
        catalog.add_item(item)
    # Normalize paths inside catalog.
    catalog.normalize_hrefs(os.path.join(os.path.dirname(zip_path), "stac"))
    # catalog.validate_all()
    # Save files if bool is set.
    if save_files:
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
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
    geojson = {
        "type": "FeatureCollection",
        "crs": {"init": "EPSG:" + str(item.properties["proj:epsg"])},
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [list(coords) for coords in item.geometry["coordinates"]]
                    ],
                },
            },
        ],
    }
    return geojson


def set_pixels_config(
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
    if mode not in PIXELS_MODES:
        raise ValueError(
            "Pixel mode not avaiable. Avaible modes: s2_stack, latest, composite."
        )
    if mode == PIXELS_S2_STACK_MODE:
        result = latest_pixel_s2_stack(**config)
    elif mode == PIXELS_LATEST_PIXEL_MODE:
        result = latest_pixel(**config)
    elif mode == PIXELS_COMPOSITE_MODE:
        result = composite(**config)

    dates = result[1]
    results = result[2]
    meta_data = result[0]
    return dates, results, meta_data


def get_and_write_raster_from_item(item, **kwargs):
    """
    Based on a pystac item get the images in timerange from item's bbox.
    Write them as a raster afterwards.

    Parameters
    ----------
        item : pystac item type
            Item representing one raster.
        kwargs : dict
            Possible parameters for config json.
    Returns
    -------
        out_path : str
            Path were the files were writen to.
    """
    # Build a configuration json for pixels.
    config = set_pixels_config(item, **kwargs)
    # Run pixels and get the dates, the images (as numpy) and the raster meta.
    dates, results, meta = run_pixels(config)
    # For a lack of out_path argument build one based on item name.
    # The directory for the raster will be one folder paralel to the stac one
    # called pixels.
    if "out_path" not in kwargs:
        work_path = os.path.dirname(os.path.dirname(item.get_root().get_self_href()))
        out_path = os.path.join(work_path, "pixels", item.id)
    else:
        out_path = kwargs["out_path"]
    # Iterate over every timestep.
    for date, np_img in zip(dates, results):
        # If the given image is empty continue to next.
        if not np_img.shape:
            continue
        # Save raster to machine or s3
        out_path_date = os.path.join(out_path, date.replace("-", "_") + ".tif")
        if not os.path.exists(os.path.dirname(out_path_date)):
            os.makedirs(os.path.dirname(out_path_date))
        write_raster(np_img, meta, out_path=out_path_date, tags={"datetime": date})
    return out_path


def build_collection_from_pixels(
    catalogs,
    path_to_pixels="",
    collection_id="",
    collection_title="",
    collection_description="",
    save_files=False,
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
    collection.normalize_hrefs(path_to_pixels)
    # collection.validate_all()
    if save_files:
        collection.save(pystac.CatalogType.SELF_CONTAINED)
    return collection


def create_and_collect(zip_path, config_file):
    """
    From a zip file containing the Y training data and a pixels configuration
    file collect pixels and build stac item.

    Parameters
    ----------
        zip_path : str
            Path to zip file containing rasters.
        config_file : dict or path to json file
            File or dictonary containing the pixels configuration.
    Returns
    -------
        final_collection : pystac collection
            Collection containing all the information from the input and collect
            data.
    """
    f = open(config_file)
    input_config = json.load(f)
    y_catalog = parse_training_data(
        zip_path, save_files=True, reference_date="2020-12-31"
    )

    if "geojson" in input_config:
        input_config.pop("geojson")

    paths_list = []
    for item in y_catalog.get_all_items():
        print(item)
        try:
            paths_list.append(get_and_write_raster_from_item(item, **input_config))
        except Exception as E:
            print(E)
            continue

    x_catalogs = []
    for folder in paths_list:
        try:
            x_cat = parse_training_data(folder, save_files=True)
        except Exception as E:
            print(E)
            continue
        x_catalogs.append(x_cat)

    x_collection = build_collection_from_pixels(
        x_catalogs, save_files=True, collection_id="x_collection"
    )
    final_collection = build_collection_from_pixels(
        [x_collection, y_catalog],
        save_files=False,
        collection_id="final",
        path_to_pixels="/home/tesselo/stac_tutorial",
    )
    return final_collection
