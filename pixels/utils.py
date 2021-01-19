import io
import math

import rasterio
from dateutil import parser
from dateutil.relativedelta import relativedelta
from rasterio import Affine
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import bounds, rasterize
from rasterio.warp import transform


def compute_transform(geojson, scale):
    """
    Compute warp parameters from geometry. The scale is expected to be in the
    coordinate system units of the geometry.
    """
    extent = bounds(geojson)
    transform = Affine(scale, 0, extent[0], 0, -scale, extent[3])
    width = math.ceil((extent[2] - extent[0]) / scale)
    height = math.ceil((extent[3] - extent[1]) / scale)

    return transform, width, height


def compute_mask(
    geojson, height, width, transform, value_column_name=None, all_touched=False
):
    """
    Compute geometry mask. If specified, the burn value for each geometry will
    be used from the value_column_name.
    """
    # Create a list of geometries, if requested with a burn value.
    if value_column_name:
        geoms_to_rasterize = [
            (dat["geometry"], dat["properties"][value_column_name])
            for dat in geojson["features"]
        ]
    else:
        geoms_to_rasterize = [dat["geometry"] for dat in geojson["features"]]

    # Rasterize the geoms.
    mask = rasterize(
        geoms_to_rasterize,
        out_shape=(height, width),
        transform=transform,
        all_touched=all_touched,
        default_value=0,
        fill=1,
    )
    # Convert to boolean mask if no value column has been specified.
    if not value_column_name:
        mask = mask.astype("bool")

    return mask


def compute_wgs83_bbox(geojson, return_bbox=False):
    """
    Computes the bounding box of the input geojson in WGS84 coordinates.
    """
    # Compute bounding box in original coordinates.
    bbox = bounds(geojson)
    # Get crs string from geojson.
    crs = (
        geojson["crs"]["init"]
        if "init" in geojson["crs"]
        else geojson["crs"]["properties"]["name"]
    )
    # Transform the bbox if necessary.
    if crs != "EPSG:4326":
        # Setup crs objects for source and destination.
        src_crs = CRS({"init": crs})
        dst_crs = CRS({"init": "EPSG:4326"})
        # Compute transformed coordinates.
        transformed_coords = transform(
            src_crs, dst_crs, (bbox[0], bbox[2]), (bbox[1], bbox[3])
        )
        # Set bbox from output.
        bbox = (
            transformed_coords[0][0],
            transformed_coords[1][0],
            transformed_coords[0][1],
            transformed_coords[1][1],
        )

    if not return_bbox:
        # Convert bounding box to geojson polygon.
        bbox = {
            "type": "Polygon",
            "coordinates": [
                [
                    [bbox[0], bbox[1]],
                    [bbox[0], bbox[3]],
                    [bbox[2], bbox[3]],
                    [bbox[2], bbox[1]],
                    [bbox[0], bbox[1]],
                ]
            ],
        }

    return bbox


def timeseries_steps(start, end, interval, intervals_per_step=1):
    """
    Construct a series of timestep intervals given the input date range.
    """
    # Convert input to dates if provided as str.
    if isinstance(start, str):
        start = parser.parse(start)
    if isinstance(end, str):
        end = parser.parse(end)
    # Compute time delta.
    delta = relativedelta(**{interval.lower(): int(intervals_per_step)})
    one_day = relativedelta(days=1)
    # Create intermediate timestamps.
    here_start = start
    here_end = start + delta
    # Loop through timesteps.
    while (here_end - one_day) <= end:
        yield here_start.date(), (here_end - one_day).date()
        # Increment intermediate timestamps.
        here_start += delta
        here_end += delta


def write_raster(
    data, args, out_path=None, driver="GTiff", dtype="float32", overviews=True, tags={}
):
    """
    Given a numpy array and necessary metadata, save a image file.
    """
    # Set the raster metadata as the same as the input
    out_meta = args
    # Ensure right shape, the first dimension of the data should be the band count.
    if len(data.shape) == 2:
        data = data.reshape((1,) + data.shape)
    # Ensure correct datatype.
    data = data.astype(dtype)
    # Update some fields to ensure COG compatability.
    out_meta.update(
        {
            "count": data.shape[0],
            "dtype": dtype,
            "driver": driver,
            "tiled": "YES",
            "compress": "DEFLATE",
        }
    )
    # Determine resampling type for overviews.
    if "int" in dtype.lower():
        resampling = Resampling.nearest
    else:
        resampling = Resampling.average
    # Determine overview factors.
    factors = [2, 4, 8, 16, 32, 64]
    # If a path is given write a image file on that path
    if out_path:
        with rasterio.open(out_path, "w", **out_meta) as dst:
            # Set the given metadata tags.
            for key, val in tags.items():
                dst.update_tags(ns="tesselo", **tags)
            dst.write(data)
            dst.build_overviews(factors, resampling)
    else:
        # Returns a memory file.
        output = io.BytesIO()
        with rasterio.io.MemoryFile() as memfile:
            with memfile.open(**out_meta) as dst:
                # Set the given metadata tags.
                dst.update_tags(ns="tesselo", **tags)
                dst.write(data)
                dst.build_overviews(factors, resampling)
            memfile.seek(0)
            output.write(memfile.read())
        output.seek(0)
        return output
