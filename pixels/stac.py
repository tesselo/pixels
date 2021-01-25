import glob
import io
import os
import zipfile
from datetime import datetime

import pystac
import rasterio
from shapely.geometry import Polygon, mapping


def get_bbox_and_footprint(raster_uri):
    """
    Get bounding box and footprint from raster
    """
    with rasterio.open(raster_uri) as ds:
        bounds = ds.bounds
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
        footprint = Polygon(
            [
                [bounds.left, bounds.bottom],
                [bounds.left, bounds.top],
                [bounds.right, bounds.top],
                [bounds.right, bounds.bottom],
            ]
        )
        if "datetime" in ds.meta:
            datetime_var = ds.meta["datetime"]
        else:
            datetime_var = datetime.datetime.now()
        return (bbox, mapping(footprint), datetime_var)


def parse_training_data(zip_path, save_files=False, description=""):
    """
    From a zip files of rasters or a folder build a stac catalog
    TODO: get datetime from raster
    """
    if zip_path.endswith(".zip"):
        # Open zip file
        archive = zipfile.ZipFile(zip_path, "r")
        # Create stac catalog
        id_name = zip_path.replace(os.path.dirname(zip_path), "").replace(".zip", "")
        raster_list = []
        for af in archive.filelist:
            raster_list.append(af.filename)
    else:
        raster_list = glob.glob(zip_path + "*/*.tif", recursive=True)

    catalog = pystac.Catalog(id=id_name, description=description)
    # For every raster in the zip file create an item, add it to catalog
    for raster in raster_list:
        if zip_path.endswith(".zip"):
            img_data = archive.read(raster)
            bytes_io = io.BytesIO(img_data)
        else:
            bytes_io = raster
        bbox, footprint, datetime_var = get_bbox_and_footprint(bytes_io)
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
    catalog.normalize_hrefs(os.path.join(os.path.dirname(zip_path), "stac"))
    if save_files:
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    return catalog
