import math
from json import JSONEncoder
from typing import Any, Iterable, List, Optional

import numpy
from dateutil import parser
from dateutil.relativedelta import relativedelta
from rasterio import Affine
from rasterio.crs import CRS
from rasterio.features import bounds, rasterize
from rasterio.warp import transform

from pixels import tio
from pixels.const import (
    BBOX_PIXEL_WITH_HEIGHT_TOLERANCE,
    S2_BAND_RESOLUTIONS,
    S2_JP2_GOOGLE_FALLBACK_URL_TEMPLATE,
    THREADS_LIMIT,
    WORKERS_LIMIT,
)
from pixels.validators import ConcurrencyOption, FeatureCollectionCRS


def compute_number_of_pixels(distance: (int, float), scale: (int, float)) -> int:
    """
    Compute number of pixels that fit into a distance considering a tolerance.

    Parameters
    ----------
    distance : int or float
        A distance between two points.
    scale : int or float
        The size of the pixel.

    Returns
    -------
    pixels_count : int
        Number of pixels.
    """
    ratio = distance / scale
    if distance % scale < BBOX_PIXEL_WITH_HEIGHT_TOLERANCE:
        return math.floor(ratio)
    else:
        return math.ceil(ratio)


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
    # Temporary fix: remove none bbbox
    if "bbox" in geojson and geojson["bbox"] is None:
        del geojson["bbox"]
    # Compute bounding box of input geojson.
    extent = bounds(geojson)
    # Compute the transform that defines the raster to create.
    transform = Affine(scale, 0, extent[0], 0, -scale, extent[3])
    # Compute with and height of the raster to create.
    width = compute_number_of_pixels(extent[2] - extent[0], scale)
    height = compute_number_of_pixels(extent[3] - extent[1], scale)
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
        Determines whether to use the all touched rasterization mode or not.


    Returns
    -------
    mask : ndarray
        The rasterized data, a boolean mask or an integer value from the value
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


def compute_wgs83_bbox(geojson: FeatureCollectionCRS, return_bbox: bool = False):
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
    # Transform the bbox if necessary.
    if geojson.rasterio_crs.to_epsg() != 4326:
        # Setup crs objects for source and destination.
        src_crs = geojson.rasterio_crs
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
    # Convert input into dates if provided as str.
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


def is_sentinel_jp2_bucket(source: str) -> bool:
    """
    Returns true if the source is a URI from the sentinel L2A JP2 bucket
    """
    return "s3://sentinel-s2-l2a/tiles/" in source


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


def jp2_to_gcs_bucket(source: str) -> str:
    """
    Transforms a URI from the AWS JP2 bucket GCS one
    """
    infofile_path = f"{source.split('/R')[0]}/productInfo.json"
    productinfo = tio.load_dictionary(infofile_path)
    tileinfo = productinfo["tiles"][0]

    return S2_JP2_GOOGLE_FALLBACK_URL_TEMPLATE.format(
        utm=str(tileinfo["utmZone"]).zfill(2),
        lat=tileinfo["latitudeBand"],
        gridsq=tileinfo["gridSquare"],
        prod=productinfo["name"],
        dtid=productinfo["datatakeIdentifier"].split("_")[2],
        time=tileinfo["datastrip"]["id"].split("_")[8][1:],
        resolution=source.split("/R")[1][:2],
        time2=productinfo["name"].split("_")[2],
        band=source.split("/")[-1].split(".jp2")[0],
    )


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


def run_concurrently(
    funk: callable,
    variable_arguments: Iterable,
    static_arguments: Optional[List[Any]] = None,
    n_jobs: Optional[int] = None,
    concurrency: Optional[ConcurrencyOption] = ConcurrencyOption.fork,
):
    """
    Run the desired function in n_jobs parallel spread iterating over
    a set of variable arguments and repeating the same static arguments
    on all the calls.

    Parameters
    ----------

        funk: callable
           The function to call in parallel
        variable_arguments: Iterable
            The series of arguments that will be varying between calls
        static_arguments: List
            The list of arguments that will be the same for all calls
        n_jobs: int
            The number of jobs (processes or threads) to parallelize in
        concurrency: ConcurrencyOption
            The way we will parallelize, usually fork or threading

    Returns
    -------

        result_list: List
            A list with whatever func returned in each call

    """
    from mpire import WorkerPool

    if static_arguments:
        iterator = unwrap_arguments([variable_arguments], static_arguments)
    else:
        iterator = variable_arguments
    if not n_jobs:
        n_jobs = len(variable_arguments)
    if concurrency == ConcurrencyOption.threading:
        max_processes = THREADS_LIMIT
    else:
        max_processes = WORKERS_LIMIT
    num_processes = min(n_jobs, max_processes)

    with WorkerPool(n_jobs=num_processes, start_method=concurrency) as pool:
        result_list = pool.map(funk, iterator)

    return result_list
