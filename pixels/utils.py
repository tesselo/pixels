import math

import rasterio
from dateutil import parser
from dateutil.relativedelta import relativedelta
from rasterio import Affine
from rasterio.crs import CRS
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


def write_raster(numpy_tensor, args, out_path=None, filetype=None, date=None):
    """
    Given a numpy array and necessary metadata, save a image file.
    """
    # Set the raster metadata as the same as the input
    out_meta = args
    # Update some fields
    out_meta.update(
        {
            "count": len(numpy_tensor),
            "compress": "DEFLATE",
        }
    )
    # If a filetype is given, set to it.
    # Possible formats: https://gdal.org/drivers/raster/index.html
    if filetype:
        out_meta.update(
            {
                "driver": filetype,
            }
        )
    # If a path is given write a image file on that path
    if out_path:
        with rasterio.open(out_path, "w", **out_meta) as dest:
            # Create a tag (metadata), with the date of the image
            dest.update_tags(date=args["date"])
            dest.write(numpy_tensor)
    # else:
    # return bytesio
    # TODO: implement the return of a ByteIO if there is no out_path
