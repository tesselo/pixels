import glob
import io
import os
import zipfile

import pystac
import rasterio
from dateutil import parser
<<<<<<< HEAD
from pixels.mosaic import composite, latest_pixel, latest_pixel_s2_stack
from pixels.utils import write_raster
=======
>>>>>>> master


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
<<<<<<< HEAD
    out_meta : rasterio meta type
        Metadata from raster.
=======
>>>>>>> master
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
<<<<<<< HEAD
        datetime_var = ds.tags(ns="tesselo").get("datetime")
        return bbox, footprint, datetime_var, ds.meta
=======
        datetime_var = ds.meta.get("datetime")

        return bbox, footprint, datetime_var
>>>>>>> master


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
<<<<<<< HEAD
        id_name = zip_path.replace(os.path.dirname(zip_path), "")
=======
>>>>>>> master
        raster_list = glob.glob(zip_path + "*/*.tif", recursive=True)

    catalog = pystac.Catalog(id=id_name, description=description)
    # For every raster in the zip file create an item, add it to catalog.
    for raster in raster_list:
        if zip_path.endswith(".zip"):
            img_data = archive.read(raster)
            bytes_io = io.BytesIO(img_data)
        else:
            bytes_io = raster
<<<<<<< HEAD
        bbox, footprint, datetime_var, out_meta = get_bbox_and_footprint(bytes_io)
=======
        bbox, footprint, datetime_var = get_bbox_and_footprint(bytes_io)
>>>>>>> master
        # Ensure datetime var is set properly.
        if datetime_var is None:
            if reference_date is None:
                raise ValueError("Datetime could not be determined for stac.")
            else:
                datetime_var = reference_date
        # Ensure datetime is object not string.
        datetime_var = parser.parse(datetime_var)
        id_raster = raster.replace(".tif", "")
<<<<<<< HEAD
        out_meta["crs"] = out_meta["crs"].to_epsg()
=======
>>>>>>> master
        item = pystac.Item(
            id=id_raster,
            geometry=footprint,
            bbox=bbox,
            datetime=datetime_var,
<<<<<<< HEAD
            properties=out_meta,
=======
            properties={},
>>>>>>> master
        )
        item.add_asset(
            key=id_raster,
            asset=pystac.Asset(
                href=zip_path + "/" + raster,
                media_type=pystac.MediaType.GEOTIFF,
            ),
        )
<<<<<<< HEAD
        crs = out_meta["crs"]
        pystac.extensions.projection.ProjectionItemExt(item).apply(crs)
        catalog.add_item(item)
    # Normalize paths inside catalog.
    catalog.normalize_hrefs(os.path.join(os.path.dirname(zip_path), "stac"))
    # Save files if bool is set,
=======
        catalog.add_item(item)
    # Normalize paths inside catalog.
    catalog.normalize_hrefs(os.path.join(os.path.dirname(zip_path), "stac"))
    # Save files if bool is set.
>>>>>>> master
    if save_files:
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    return catalog


<<<<<<< HEAD
def build_bbox_geojson(item):
    """Build GeoJson from item bounding box.

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
    """Based on a item build a config file to use on pixels.

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
    geojson = build_bbox_geojson(item)
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
    """Run pixels, based on a config file and a chosen mode.

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
    if mode not in ("s2_stack", "latest", "composite"):
        raise ValueError(
            "Pixel mode not avaiable. Avaible modes: s2_stack, latest, composite."
        )
    if mode == "s2_stack":
        result = latest_pixel_s2_stack(**config)
    elif mode == "latest":
        result = latest_pixel(**config)
    elif mode == "composite":
        result = composite(**config)

    dates = result[1]
    results = result[2]
    meta_data = result[0]
    return dates, results, meta_data


def get_and_write_raster_from_item(item, **kwargs):
    """Based on a pystac item get the images in timerange from item's bbox.
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
    config = set_pixels_config(item, **kwargs)
    dates, results, meta = run_pixels(config)
    if "out_path" not in kwargs:
        work_path = os.path.dirname(os.path.dirname(item.get_root().get_self_href()))
        out_path = work_path + "/pixels/" + item.id
    else:
        out_path = kwargs["out_path"]
    for date, np_img in zip(dates, results):
        if not np_img.shape:
            continue
        # Save raster to machine or s3
        out_path_date = out_path + "/" + date.replace("-", "_") + ".tif"
        if not os.path.exists(os.path.dirname(out_path_date)):
            os.makedirs(os.path.dirname(out_path_date))
        write_raster(np_img, meta, out_path=out_path_date, tags={"datetime": date})
        # build item to new catalog
    return out_path


def build_collection_from_pixels(path_to_pixels):
    """From a path to multiple rasters build a pystact collection of catalogs.
        Each catalog being a location with multiple timesteps.
        Each catalog corresponds to a Y-input.
        TODO: the all function
    Parameters
    ----------
        path_to_pixels : str
    Returns
    -------
        collection : pystact collection
    """
    return
=======
def set_pixels_config(catalog):
    """
    Based on a catalog build a config file to use on pixels.

    Parameters
    ----------

    Returns
    -------

    """
    config = {}
    return config
>>>>>>> master
