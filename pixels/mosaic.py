from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool

import numpy
import sentry_sdk
import structlog
from rasterio.errors import RasterioIOError

from pixels.clouds import pixels_mask
from pixels.const import LANDSAT_1_LAUNCH_DATE, NODATA_VALUE
from pixels.exceptions import PixelsException
from pixels.retrieve import retrieve
from pixels.search import search_data
from pixels.utils import compute_mask, timeseries_steps

# Get logger
logger = structlog.get_logger(__name__)

BANDS_REQUIRED_FOR_COMPOSITES = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12"]


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
        it is empty or None, all bands will be extracted.
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

    Returns
    -------
    creation_args : dict
        The creation arguments metadata for the extracted pixel matrix. Can be
        used to write the extracted pixels to a file if desired.
    first_end_date : date object
        The date of the first scene used to create the output image.
    stack : numpy array
        The extracted pixel stack, with shape (bands, height, width).
    """
    if not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    # Skip search if list of scenes was provided, otherwise assume input is a specific end_date to search with.
    if isinstance(end_date, (list, tuple)):
        logger.debug(f"Latest pixels for {len(end_date)} items.")
        items = end_date
    else:
        items = search_data(
            geojson=geojson,
            start=LANDSAT_1_LAUNCH_DATE,
            end=end_date,
            limit=limit,
            platforms=platforms,
            maxcloud=maxcloud,
            level=level,
            sensor=sensor,
        )

        if not items:
            raise ValueError("No scenes in search response. Latest Pixel.")

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
        band_list = [
            (item["bands"][band], geojson, scale, False, False, False, None)
            for band in bands
        ]

        data = []
        failed_retrieve = False
        if pool:
            try:
                with ThreadPoolExecutor(max_workers=len(bands)) as executor:
                    # Submit band retrieval tasks to pool.
                    futures = []
                    for band in band_list:
                        futures.append(executor.submit(retrieve, *band))
                    # Process completed tasks.
                    for future in futures:
                        result = future.result()
                        data.append(result)
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

    retrieve_pool = False

    if interval == "all":
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
            raise ValueError("No scenes in search response. pixel_stack")

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
        funk = latest_pixel
    else:
        if mode == "latest_pixel":
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
            funk = latest_pixel
        elif mode == "composite":
            platforms = "SENTINEL_2"
            shadow_threshold = 0.1
            light_clouds = True
            sort = "cloud_cover"
            finish_early_cloud_cover_percentage = 0.05
            # Extend bands to necessary parts.
            missing = [
                band for band in BANDS_REQUIRED_FOR_COMPOSITES if band not in bands
            ]
            bands = list(bands) + missing
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
                )
                for step in timeseries_steps(start, end, interval, interval_step)
            ]
            funk = composite

        logger.info(
            "Getting {} {} {} images for this stack.".format(len(dates), interval, mode)
        )

    # Get pixels.
    pool_size = min(len(dates), pool_size)
    logger.info("Processing pool size is {}.".format(pool_size))

    result = []
    if pool_size > 1:
        with Pool(pool_size) as p:
            result = p.starmap(funk, dates)
    else:
        for date in dates:
            result.append(funk(*date))

    # Remove results that are empty.
    result = [dat for dat in result if dat[2] is not None]
    result = [dat for dat in result if not numpy.all(dat[2][0] == NODATA_VALUE)]

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

    # Check band list.
    BANDS_REQUIRED_FOR_COMPOSITES = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12"]
    missing = [band for band in BANDS_REQUIRED_FOR_COMPOSITES if band not in bands]
    if missing:
        raise ValueError("Missing {} bands for composite.".format(missing))

    required_band_indices = [
        bands.index(band) for band in BANDS_REQUIRED_FOR_COMPOSITES
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
        raise ValueError("No features in search response. composite")

    stack = None
    creation_args = None
    mask = None
    first_end_date = None
    for item in items:
        if first_end_date is None:
            first_end_date = str(items[0]["sensing_time"].date())
        # Prepare band list.
        band_list = [
            (item["bands"][band], geojson, scale, False, False, False, None)
            for band in bands
        ]

        if pool:
            with Pool(len(bands)) as p:
                data = p.starmap(retrieve, band_list)
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
            for i in range(len(bands)):
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

    return creation_args, first_end_date, numpy.array(stack)
