import glob
import io
import os
import zipfile

import pystac
import rasterio
from dateutil import parser


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
        datetime_var = ds.meta.get("datetime")

        return bbox, footprint, datetime_var


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
        raster_list = glob.glob(zip_path + "*/*.tif", recursive=True)

    catalog = pystac.Catalog(id=id_name, description=description)
    # For every raster in the zip file create an item, add it to catalog.
    for raster in raster_list:
        if zip_path.endswith(".zip"):
            img_data = archive.read(raster)
            bytes_io = io.BytesIO(img_data)
        else:
            bytes_io = raster
        bbox, footprint, datetime_var = get_bbox_and_footprint(bytes_io)
        # Ensure datetime var is set properly.
        if datetime_var is None:
            if reference_date is None:
                raise ValueError("Datetime could not be determined for stac.")
            else:
                datetime_var = reference_date
        # Ensure datetime is object not string.
        datetime_var = parser.parse(datetime_var)
        id_raster = raster.replace(".tif", "")
        item = pystac.Item(
            id=id_raster,
            geometry=footprint,
            bbox=bbox,
            datetime=datetime_var,
            properties={},
        )
        item.add_asset(
            key=id_raster,
            asset=pystac.Asset(
                href=zip_path + "/" + raster,
                media_type=pystac.MediaType.GEOTIFF,
            ),
        )
        catalog.add_item(item)
    # Normalize paths inside catalog.
    catalog.normalize_hrefs(os.path.join(os.path.dirname(zip_path), "stac"))
    # Save files if bool is set.
    if save_files:
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    return catalog


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
