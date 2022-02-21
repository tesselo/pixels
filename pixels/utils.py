import io
import math
from json import JSONEncoder
from multiprocessing import Pool
from typing import Any, Iterable, List, Optional

import numpy
import rasterio
import sentry_sdk
import structlog
from dateutil import parser
from dateutil.relativedelta import relativedelta
from rasterio import Affine
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import bounds, rasterize
from rasterio.warp import transform

from pixels.const import S2_BAND_RESOLUTIONS, WORKERS_LIMIT

logger = structlog.get_logger(__name__)


def compute_transform(geojson, scale):
    """
    Compute raster transform parameters from geometry.

    Computes the data necessary to create a raster based on an input geojson
    dictionary. The geojson dictionary can have a non-standard CRS specified.
    The scale argument is expected to be in the coordinate system units of the
    geometry.


    Parameters
    ----------
    geojson : dict
        A geojson object that will be used for computing the bounding box.
    scale : float or int
        The scale for the output transform, in the CRS of the input geometry.

    Returns
    -------
    transform : Affine
        An affine transform for the bbox of the input geojson.

    width : int
        Pixel width for raster.

    height : int
        Pixel height for raster.
    """
    # Compute bounding box of input geojson.
    extent = bounds(geojson)
    # Compute the transform that defines the raster to create.
    transform = Affine(scale, 0, extent[0], 0, -scale, extent[3])
    # Compute with and height of the raster to create.
    width = math.ceil((extent[2] - extent[0]) / scale)
    height = math.ceil((extent[3] - extent[1]) / scale)

    return transform, width, height


def compute_mask(
    geojson, height, width, transform, value_column_name=None, all_touched=False
):
    """
    Burn a geometry into a raster.

    Returns a numpy array with the rasterized version of the input geometries.
    The burn value by default is a boolean. This can be made more fine grained
    by specifying a column containing the burn value for each geometry.

    Parameters
    ----------
    gejson : dict
        Geometric data for rasterization.
    height : int
        Height of the mask array.
    width : int
        Width of the mask array.
    transform : Affine
        Transform for the rasterization.
    value_column_name : str or None, optional
        Name of the value attribute in the geojson that is used as burn value.
    all_touched : bool or None, optional
        Wether to use the all touched rasterization mode or not.


    Returns
    -------
    mask : ndarray
        The rasterized data, a boolean mask or a integer value from the value
        column.
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

    Parameters
    ----------
    gejson : dict
        Geometric data from which to compute a bounding box.
    return_bbox : bool or None, optional
        If True, a simple bbox tuple is returned (xmin, ymin, xmax, ymax). If
        False, the bbox is returned as geojson polygon feature.

    Returns
    -------
    bbox : tuple or dict
        The bounding box of the input geometry. Either as tuple or geojson
        feature.
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


def timeseries_steps(start, end, interval, interval_step=1):
    """
    Construct a series of timestep intervals.

    The intervals are from the start to the end date, in a fixed interval size.
    Two dimensions define the intervals, the unit and the units per step. For
    example, with a week interval and 2 steps by interval, the date ranges are
    two weeks at a time.

    Parameters
    ----------
    start : str
        A parseable date or datetime string. Represents the start date of the
        intervals. Example "2020-01-01".
    end : str
        A parseable date or datetime string. Represents the end date of the
        intervals. Example "2020-12-31".
    interval : str
        A timestep interval. Needs to be interpretable by relativedelta. Valid
        values include "years", "months", "weeks", and "days".
    interval_step : int, optional
        The number of times the interval is counted as step. For instance, with
        interval weeks and interval_step 2, two weeks are the step size.

    Returns
    -------
    intervals : list of tuples
        A list of date tuples. Each tuple is of length two, representing the
        start and end date of a single interval.
    """
    # Convert input to dates if provided as str.
    if isinstance(start, str):
        start = parser.parse(start)
    if isinstance(end, str):
        end = parser.parse(end)
    # Compute time delta.
    delta = relativedelta(**{interval.lower(): int(interval_step)})
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
    Convert a numpy array into a raster object.

    Given a numpy array and necessary metadata, create either an raster on disk
    or return the raster in memory as a binary IO buffer. To create a file on
    disk, provide an output path.

    Parameters
    ----------
    data : array_like
        The pixel values for the raster as numpy array.
    args : dict
        Rasterio creation arguments for the new raster.
    out_path : str, optional
        The path where the new file should be written on disk. If not provided,
        a BytesIO object is returned with the raster in memory.
    driver : str, optional
        Rasterio driver for creating the new raster.
    dtype : str, optional
        Data type string specifying the output datatype.
    overviews : bool, optional
        Shall internal overviews be created for the new raster.
    tags : dict, optional
        A dictionary of tags to be added to the raster file. The namespace for
        all tags will be "tesselo".

    Returns
    -------
    raster : BytesIO or None
        If an output path was provided, the raster is written on disk and None
        is returned. Otherwise, the raster is returned as a binary blob in
        memory.
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
    if "int" in str(dtype).lower():
        resampling = Resampling.nearest
    else:
        resampling = Resampling.average
    # Determine overview factors.
    factors = [(2 ** a) for a in range(1, 7) if (2 ** a) < data.shape[-1]]
    # factors = [2, 4, 8, 16, 32, 64]
    # If a path is given write a image file on that path
    if out_path:
        with rasterio.open(out_path, "w", **out_meta) as dst:
            # Set the given metadata tags.
            for key, val in tags.items():
                dst.update_tags(**tags)
            dst.write(data)
            try:
                dst.build_overviews(factors, resampling)
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.warning(f"Error in saving raster, building overviews: {e}")
    else:
        # Returns a memory file.
        output = io.BytesIO()
        with rasterio.io.MemoryFile() as memfile:
            with memfile.open(**out_meta) as dst:
                # Set the given metadata tags.
                dst.update_tags(**tags)
                dst.write(data)
                # To be able to build the overviews we need to have a size
                # bigger than the factors.
                try:
                    dst.build_overviews(factors, resampling)
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    logger.warning(f"Error in saving raster, building overviews: {e}")
            memfile.seek(0)
            output.write(memfile.read())
        output.seek(0)
        return output


class NumpyArrayEncoder(JSONEncoder):
    """
    Custom encoder for numpy arrays.
    """

    def default(self, obj):

        if isinstance(obj, numpy.ndarray):
            return obj.tolist()

        return JSONEncoder.default(self, obj)


def is_sentinel_cog_bucket(source: str) -> bool:
    """
    Returns true if the source is a URI from the sentinel COG bucket
    """
    return "sentinel-cogs.s3.us-west-2.amazonaws.com" in source


def cog_to_jp2_bucket(source: str) -> str:
    """
    Transforms a URI from the COG optimized bucket to the JP2 one
    """
    parts = source.split("/")

    day = int(parts[-2].split("_")[2][-2:])
    band = parts[-1].split(".tif")[0]
    scene_count = int(parts[-2].split("_")[3])
    resolution = S2_BAND_RESOLUTIONS[band]

    return f"s3://sentinel-s2-l2a/tiles/{'/'.join(parts[4:-2])}/{day}/{scene_count}/R{resolution}m/{band}.jp2"


def unwrap_arguments(variable_arguments: List[Iterable], static_arguments: List[Any]):
    """
    Returns an iterator that will traverse over n sets of variable parameters
    and 1 set of static parameters, resulting in an n+1 elements tuple per iteration.

    Parameters
    ----------
        variable_arguments : list of iterables
            Variables to iterate over.
        static_arguments : list
            Variables to repeat on every iteration.

    Returns
    -------
        generator : tuple
            Yields all the variable arguments and the static one.
            (var_argA_0, var_argB_0, ..., static1, static2, ...)
            (var_argA_1, var_argB_1, ..., static1, static2, ...)
    """
    for args in zip(*variable_arguments):
        yield (*args, *static_arguments)


def run_starmap_multiprocessing(
    func: callable,
    variable_arguments: Iterable,
    static_arguments: List[Any],
    iterator_size: Optional[int] = None,
    workers_limit: Optional[int] = WORKERS_LIMIT,
):
    iterator = unwrap_arguments([variable_arguments], static_arguments)
    if not iterator_size:
        iterator_size = len(variable_arguments)
    num_processes = min(iterator_size, workers_limit)

    with Pool(processes=num_processes) as pool:
        result_list = pool.starmap(func=func, iterable=iterator)

    return result_list
