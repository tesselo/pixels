import datetime
from concurrent.futures import ThreadPoolExecutor

import numpy
import sentry_sdk
import structlog
from rasterio.errors import RasterioIOError

from pixels.clouds import pixels_mask
from pixels.const import (
    DISCRETE_BANDS,
    LANDSAT_1_LAUNCH_DATE,
    MAX_COMPOSITE_BAND_WORKERS,
    NODATA_VALUE,
    S2_BANDS_REQUIRED_FOR_COMPOSITES,
)
from pixels.exceptions import PixelsException
from pixels.retrieve import retrieve
from pixels.search import search_data
from pixels.utils import compute_mask, timeseries_steps

# Get logger
logger = structlog.get_logger(__name__)


def calculate_start_date(end_date):
    """
    Calculates the start date range given the end_date

    Parameters
    ----------

    end_date: str, datetime, list, tuple, dict
    """

    # TODO: remove these type checks after latest_pixels arguments sanitization
    if isinstance(end_date, (str, datetime.date, datetime.datetime)):
        if isinstance(end_date, str):
            try:
                end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise PixelsException(f"Invalid end date: {end_date}")
        else:
            end_datetime = end_date

        start_datetime = end_datetime - datetime.timedelta(days=31)
        start_date = start_datetime.strftime("%Y-%m-%d")
    else:
        # We can't calculate the start_date, but current function calls
        # are expecting this function to receive arrays or dictionaries
        # See https://app.asana.com/0/1200570555980604/1201746409030114/f
        start_date = LANDSAT_1_LAUNCH_DATE
    return start_date


def latest_pixel(
    geojson,
    end_date,
    scale,
    bands=None,
    platforms=None,
    limit=10,
    clip=False,
    pool=False,
    maxcloud=None,
    level=None,
    sensor=None,
    start_date=None,
):
    """
    Get the latest pixel for the input items over the input fetures.

    Parameters
    ----------
    geojson : dict
        The area over which the raster data will be collected. The geometry
        extent will be used as bounding box for the raster. A custom CRS
        property can be used to define the projection.
    end_date : str
        A parseable date or datetime string. Represents the maximum date of the
        input imagery. Only images before that date will be used for creating
        the output. Example "2020-12-31".
    scale : int or float
        The scale (resolution) of the output raster. This number needs to be in
        the uints of the input geojson. If not provided, the scale of the input
        raster is used, but only if the projection of the raster is the same as
        the projection of the geojson.
    bands : list of int, optional
        Defines which band indices shall be extracted from the source raster. If
        it is empty or None, all bands will be extracted. #NOT WORKING WHEN WE DON'T PASS BANDS LIST
    platforms : str or list, optional
        The selection of satellites to search for images on pixels. The satellites
        can be from Landsat collection or Sentinel 2. The str or list must contain
        the following values: 'SENTINEL_2', 'LANDSAT_1', 'LANDSAT_2', 'LANDSAT_3',
        'LANDSAT_4', 'LANDSAT_5', 'LANDSAT_7' or'LANDSAT_8'. If ignored, it returns
        values from different platforms according to the combination of the other
        parameters.
    limit: integer
        Limit the number of images that will be listed as candidates for
        extracting pixels.
    clip : boolean, optional
        If True, the raster is clipped against the geometry. All values outside
        the geometry will be set to nodata.
    pool : boolean, optional
        If True, thread pooling is used to request the image data.
    maxcloud : int, optional
        Maximun accepted cloud coverage in images. If not provided returns records with
        up to 100% cloud coverage.
    level : str, optional
        The level of image processing for Sentinel-2 satellite. It can be 'L1C'(Level-1C)
        or 'L2A'(Level-2A) that provides Bottom Of Atmosphere (BOA) reflectance images
        derived from associated Level-1C products. Ignored if platforms is not Sentinel 2.
    sensor: str, optional
        Sensor mode for Landsat 1-5. Must be one of be TM or MSS.
    start_date : str, datetime, optional
        A parseable date or datetime string. Represents the starting date of the
        input imagery. Only images after that date will be used for creating
        the output. Example "2020-12-1". The default is 31 days before start_date
        when start_date is not an array or a dictionary, in that case it will be
        LANDSAT_1_LAUNCH_DATE.

    Returns
    -------
    creation_args : dict or None
        The creation arguments metadata for the extracted pixel matrix. Can be
        used to write the extracted pixels to a file if desired.
    first_end_date : date object or None
        The date of the first scene used to create the output image.
    stack : numpy array or None
        The extracted pixel stack, with shape (bands, height, width).
    """
    if not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    if start_date is None:
        start_date = calculate_start_date(end_date)

    # Skip search if list of scenes was provided, otherwise assume input is a specific end_date to search with.
    # TODO: do not reuse parameters for other than the documented in the docstring
    # TODO: and with a purpose that does not fit the name of the argument
    if isinstance(end_date, (list, tuple)):
        logger.debug(f"Latest pixels for {len(end_date)} items.")
        items = end_date
    else:
        items = search_data(
            geojson=geojson,
            start=start_date,
            end=end_date,
            limit=limit,
            platforms=platforms,
            maxcloud=maxcloud,
            level=level,
            sensor=sensor,
        )
        # Return early if no items could be found.
        if not items:
            logger.info(
                "No scenes in search response.",
                funk="latest_pixel",
                search_date_end=end_date,
                search_date_start=start_date,
            )
            return None, None, None

    # Assign variables to be populated during pixel collection.
    stack = None
    first_end_date = None
    creation_args = {}
    mask = None
    # Get data for each item.
    for item in items:
        logger.debug(item["product_id"])
        # Track first end date (highest priority image in stack).
        if first_end_date is None:
            first_end_date = str(items[0]["sensing_time"].date())
        # Prepare band list.
        band_list = []
        for band in bands:
            if band not in item["bands"]:
                raise PixelsException(
                    f"Latest pixel requested for a band not present: {band} in {item['base_url']}"
                )
            band_list.append(
                (
                    item["bands"][band],
                    geojson,
                    scale,
                    True if band in DISCRETE_BANDS else False,
                    False,
                    False,
                    None,
                )
            )

        data = []
        failed_retrieve = False
        if pool:
            try:
                with ThreadPoolExecutor(max_workers=len(bands)) as executor:
                    futures = [executor.submit(retrieve, *band) for band in band_list]
                    data = [future.result() for future in futures]
            except RasterioIOError as e:
                sentry_sdk.capture_exception(e)
                logger.warning(f"Rasterio IO Error. item {RasterioIOError}")
                failed_retrieve = True
        else:
            for band in band_list:
                try:
                    result = retrieve(*band)
                except RasterioIOError as e:
                    sentry_sdk.capture_exception(e)
                    logger.warning(f"Rasterio IO Error. item {RasterioIOError}")
                    failed_retrieve = True
                    break
                data.append(result)

        # Continue to next scene if retrieval of bands failed.
        if failed_retrieve:
            logger.warning(
                "Failed retrieval of bands for {}, continuing.".format(
                    item["product_id"]
                )
            )
            continue

        # Continue if this scene was empty.
        if any([dat[1] is None for dat in data]):
            continue

        # Create stack.
        if stack is None:
            # Set first return as stack.
            stack = [dat[1] for dat in data]
        else:
            # Update nodata values in stack with new pixels.
            for i in range(len(bands)):
                stack[i][mask] = data[i][1][mask]

        # Extract creation arguments.
        if not creation_args:
            creation_args = data[0][0]

        # Update nodata mask.
        mask = stack[0] == NODATA_VALUE

        # If all pixels were populated stop getting more data.
        if not numpy.any(mask):
            break

    # Final polishing of stack data.
    if stack is not None:
        # Clip stack to geometry if requested.
        if clip and creation_args:
            mask = compute_mask(
                geojson,
                creation_args["height"],
                creation_args["width"],
                creation_args["transform"],
            )
            for i in range(len(stack)):
                stack[i][mask] = NODATA_VALUE
        # Ensuri the stack is a numpy array.
        stack = numpy.array(stack)

    return creation_args, first_end_date, stack


def pixel_stack(
    geojson,
    start,
    end,
    scale,
    interval="weeks",
    interval_step=1,
    bands=None,
    platforms="SENTINEL_2",
    limit=100,
    clip=False,
    maxcloud=None,
    pool_size=5,
    level=None,
    sensor=None,
    mode="latest_pixel",
):
    """
    Get the latest pixel at regular intervals between two dates.
    """
    # Check if is list or tuple
    if not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    retrieve_pool = True

    if mode == "all" or interval == "all":
        # For all mode, the date range is constructed around each scene, and
        # then latest pixel is used for each date. This way, latest pixel will
        # only have one possible input every time.
        funk = latest_pixel
        # Get all scenes of for this date range.
        response = search_data(
            geojson=geojson,
            start=start,
            end=end,
            limit=limit,
            platforms=platforms,
            maxcloud=maxcloud,
            level=level,
            sensor=sensor,
        )

        if not response:
            logger.info(
                "No scenes in search response.",
                funk="pixel_stack",
                search_date_end=end,
                search_date_start=start,
            )
            return None, None, None

        logger.info("Getting {} scenes for this stack.".format(len(response)))

        dates = [
            (
                geojson,
                [item],
                scale,
                bands,
                platforms,
                limit,
                clip,
                retrieve_pool,
                maxcloud,
                level,
            )
            for item in response
        ]
    elif mode == "latest_pixel":
        funk = latest_pixel
        # Construct array of latest pixel calls with varying dates.
        dates = [
            (
                geojson,
                step[1],
                scale,
                bands,
                platforms,
                limit,
                clip,
                retrieve_pool,
                maxcloud,
                level,
            )
            for step in timeseries_steps(start, end, interval, interval_step)
        ]
    elif mode == "composite":
        funk = composite
        platforms = "SENTINEL_2"
        shadow_threshold = 0.1
        light_clouds = True
        sort = "cloud_cover"
        finish_early_cloud_cover_percentage = 0.05
        composite_method = "SCL"
        # Create input list with date ranges.
        dates = [
            (
                geojson,
                step[0],
                step[1],
                scale,
                bands,
                limit,
                clip,
                retrieve_pool,
                maxcloud,
                shadow_threshold,
                light_clouds,
                level,
                sort,
                finish_early_cloud_cover_percentage,
                platforms,
                composite_method,
            )
            for step in timeseries_steps(start, end, interval, interval_step)
        ]

    if mode != "all":
        logger.info(
            "Getting {} {} {} images for this stack.".format(len(dates), interval, mode)
        )

    # Get pixels.
    pool_size = min(len(dates), pool_size)
    logger.info("Processing pool size is {}.".format(pool_size))

    result = []
    if pool_size > 1:
        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            futures = [executor.submit(funk, *date) for date in dates]
            result = [future.result() for future in futures]
    else:
        for date in dates:
            result.append(funk(*date))

    # Remove results that are none.
    result = [dat for dat in result if dat[2] is not None]
    # Remove results that are all nodata.
    result = [
        dat
        for dat in result
        if dat[2].ndim and not numpy.all(dat[2][0] == NODATA_VALUE)
    ]

    # Return early if no results are left after cleaning.
    if not result:
        logger.info(
            "No scenes in search response.",
            funk="pixel_stack",
            search_date_end=end,
            search_date_start=start,
        )
        return None, None, None

    # Convert to individual arrays.
    creation_args = result[0][0]
    dates = [dat[1] for dat in result]
    pixels = numpy.array([dat[2] for dat in result])

    return creation_args, dates, pixels


def composite(
    geojson,
    start,
    end,
    scale,
    bands=["B02", "B03", "B04", "B08", "B8A", "B11", "B12"],
    limit=10,
    clip=False,
    pool=False,
    maxcloud=None,
    shadow_threshold=0.1,
    light_clouds=True,
    level="L2A",
    sort="cloud_cover",
    finish_early_cloud_cover_percentage=0.05,
    platforms="SENTINEL_2",
    composite_method="SCL",
):
    """
    Get the composite over the input features.
    """
    logger.info("Compositing pixels from {} to {}".format(start, end))
    # Check if is list or tuple
    if not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    # Currently limit to S2 and L2A.
    if len(platforms) > 1 or platforms[0] != "SENTINEL_2" or level != "L2A":
        raise PixelsException(
            "For composites platforms and level must be Sentinel-2 L2A."
        )
    # Copy band list to avoid race conditions.
    bands_copy = bands.copy()
    # Check band list.
    if composite_method == "SCL":
        remove_scl_from_output = False
        if "SCL" not in bands_copy:
            bands_copy.append("SCL")
            # If the SCL band has not been requested for output, remove it
            # from the stack before returning the result.
            remove_scl_from_output = True
        scl_band_index = bands_copy.index("SCL")
    else:
        missing = [
            band for band in S2_BANDS_REQUIRED_FOR_COMPOSITES if band not in bands_copy
        ]
        if missing:
            raise PixelsException("Missing {} bands for composite.".format(missing))
        required_band_indices = [
            bands_copy.index(band) for band in S2_BANDS_REQUIRED_FOR_COMPOSITES
        ]

    # Search scenes.
    items = search_data(
        geojson=geojson,
        start=start,
        end=end,
        limit=limit,
        platforms=["SENTINEL_2"],
        maxcloud=maxcloud,
        level=level,
        sort="cloud_cover",
    )

    if not items:
        logger.info(
            "No scenes in search response.",
            funk="composite",
            search_date_end=end,
            search_date_start=start,
        )
        return None, None, None

    stack = None
    creation_args = None
    mask = None
    first_end_date = None
    for item in items:
        if first_end_date is None:
            first_end_date = str(items[0]["sensing_time"].date())
        # Prepare band list.
        band_list = [
            (
                item["bands"][band],
                geojson,
                scale,
                True if band in DISCRETE_BANDS else False,
                False,
                False,
                None,
            )
            for band in bands_copy
        ]

        if pool:
            max_workers = min(MAX_COMPOSITE_BAND_WORKERS, len(band_list))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(retrieve, *band) for band in band_list]
                data = [future.result() for future in futures]
        else:
            data = []
            for band in band_list:
                data.append(retrieve(*band))
        # Get creation args from first result.
        if creation_args is None:
            creation_args = data[0][0]
        # Continue if this image was all nodata (retrieve returns None).
        if any([dat[1] is None for dat in data]):
            continue
        # Add scene to stack.
        layer = numpy.array([dat[1] for dat in data])
        if composite_method == "SCL":
            # SCL classes.
            # 0: NO_DATA
            # 1: SATURATED_OR_DEFECTIVE
            # 2: DARK_AREA_PIXELS
            # 3: CLOUD_SHADOWS
            # 4: VEGETATION
            # 5: NOT_VEGETATED
            # 6: WATER
            # 7: UNCLASSIFIED
            # 8: CLOUD_MEDIUM_PROBABILITY
            # 9: CLOUD_HIGH_PROBABILITY
            # 10: THIN_CIRRUS
            # 11: SNOW
            layer_clouds = numpy.isin(layer[scl_band_index], [0, 1, 3, 7, 8, 9, 10])
        else:
            # Compute cloud mask for new layer.
            layer_clouds = pixels_mask(
                *(layer[idx] for idx in required_band_indices),
                light_clouds=light_clouds,
                shadow_threshold=shadow_threshold,
            )
            # Shadow mask only uses RGB, so limit to first three bands.
            logger.debug(
                "Layer masked count {} %".format(
                    int(100 * numpy.sum(layer_clouds) / layer_clouds.size)
                )
            )
        # Create stack.
        if stack is None:
            # Set first return as stack.
            stack = layer
            mask = layer_clouds
        else:
            # Update nodata values in stack with new pixels.
            for i in range(len(bands_copy)):
                stack[i][mask] = data[i][1][mask]
            # Update cloud mask.
            mask = mask & layer_clouds

        logger.debug(
            "Remaining masked count {} %".format(int(100 * numpy.sum(mask) / mask.size))
        )
        # If no cloudy pixels are left, stop getting more data.
        if numpy.sum(mask) / mask.size <= finish_early_cloud_cover_percentage:
            logger.debug("Finalized compositing early.")
            break

    # Clip stack to geometry if requested.
    if stack is not None:
        if clip and creation_args:
            mask = compute_mask(
                geojson,
                creation_args["height"],
                creation_args["width"],
                creation_args["transform"],
            )
            for i in range(len(stack)):
                stack[i][mask] = NODATA_VALUE

    # Remove scl if required.
    if remove_scl_from_output:
        stack = numpy.delete(stack, scl_band_index, 0)

    return creation_args, first_end_date, numpy.array(stack)
