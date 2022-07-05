import numpy as np
import pystac
import rasterio
from pystac import STAC_IO

from pixels import tio
from pixels.utils import check_for_squared_pixels


def write_method(uri, txt):
    if tio.is_remote(uri):
        tio.write(uri, txt)
    else:
        STAC_IO.default_write_text_method(uri, txt)


def read_method(uri):
    if tio.is_remote(uri):
        return tio.read(uri)
    else:
        return STAC_IO.default_read_text_method(uri)


def get_catalog_length(catalog_path):
    # Try opening link as collection. If this fails, try opening it as catalog.
    try:
        collection = pystac.Collection.from_file(catalog_path)
        size = len(collection.get_child_links())
    except KeyError:
        catalog = pystac.Catalog.from_file(catalog_path)
        size = len(catalog.get_item_links())
    return size


def get_bbox_and_footprint_and_stats(
    raster_uri, categorical, bins=10, hist_range=(0, 100)
):
    """with open(path, "r") as file:
        file.write(json.dumps(catalog_dict))
    Get bounding box and footprint from raster.

    Parameters
    ----------
    raster_uri : str or bytes_io
        The raster file location or bytes_io.
    categorical: boolean, optional
        If True, compute statistics of the pixel data for class weighting.
    bins: int, optional
        Number of bins to use in histogram.
    hist_range: tuple, optional
        Range of histogram.

    Returns
    -------
    bbox : list
        Bounding box of input raster.
    footprint : list
        Footprint of input raster.
    datetime : datetime type
        Datetime from image.
    out_meta : rasterio meta type
        Metadata from raster.
    stats: dict or None
        Statistics of the data, counts by unique value or histogram.
    """
    with rasterio.open(raster_uri) as ds:
        check_for_squared_pixels(ds)
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

        datetime = ds.tags().get("datetime")
        # Compute unique counts if requested.
        img = ds.read()
        if categorical:
            unique_values, unique_counts = np.unique(img, return_counts=True)
            stats = {
                int(key): int(val) for key, val in zip(unique_values, unique_counts)
            }
        else:
            hist, bin_edges = np.histogram(img, bins=bins, range=hist_range)
            stats = {int(key): int(val) for key, val in zip(hist, bin_edges)}

        return bbox, footprint, datetime, ds.meta, stats
