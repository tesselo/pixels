import logging
from multiprocessing import Pool

import numpy
from rasterio.errors import RasterioIOError

from pixels.clouds import cloud_or_snow_mask, composite_index, shadow_mask
from pixels.const import LANDSAT_1_LAUNCH_DATE, NODATA_VALUE
from pixels.retrieve import retrieve
from pixels.search import search_data
from pixels.utils import compute_mask, timeseries_steps

# Get logger
logger = logging.getLogger(__name__)


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
):
    """
    Get the latest pixel for the input items over the input fetures.
    """
    if not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    # Skip search if list of scenes was provided, otherwise assume input is a specific end_date to search with.
    if isinstance(end_date, (list, tuple)):
        logger.info("Latest pixels for {} items.".format(len(end_date)))
        items = end_date
    else:
        items = search_data(
            geojson=geojson,
            start=LANDSAT_1_LAUNCH_DATE,
            end=end_date,
            limit=limit,
            platforms=platforms,
            maxcloud=maxcloud,
        )

        if not items:
            raise ValueError("No scenes in search response.")

    # Assign variables to be populated during pixel collection.
    stack = None
    first_end_date = None
    creation_args = {}
    mask = None
    # Get data for each item.
    for item in items:
        logger.info(item["product_id"])
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
            with Pool(len(bands)) as p:
                try:
                    data = p.starmap(retrieve, band_list)
                except RasterioIOError:
                    failed_retrieve = True
        else:
            for band in band_list:
                try:
                    result = retrieve(*band)
                except RasterioIOError:
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

        # Create stack.
        if stack is None:
            # Set first return as stack.
            stack = [dat[1] for dat in data]
            # Extract creation arguments.
            creation_args = data[0][0]
        else:
            # Update nodata values in stack with new pixels.
            for i in range(len(bands)):
                stack[i][mask] = data[i][1][mask]

        # Update nodata mask.
        mask = stack[0] == NODATA_VALUE

        # If all pixels were populated stop getting more data.
        if not numpy.any(mask):
            break

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

    return creation_args, first_end_date, stack


def latest_pixel_s2_stack(
    geojson,
    start,
    end,
    scale,
    interval="weeks",
    bands=None,
    platforms="SENTINEL_2",
    limit=10,
    clip=False,
    maxcloud=None,
    pool_size=20,
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
        )

        if not response:
            raise ValueError("No scenes in search response.")

        logger.info("Getting {} scenes for this geom.".format(len(response)))

        limit = 5
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
            )
            for item in response
        ]
    else:
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
            )
            for step in timeseries_steps(start, end, interval)
        ]
        logger.info("Getting {} {} for this geom.".format(len(dates), interval))

    # Get pixels.
    pool_size = min(len(dates), pool_size)
    logger.info(
        "Found {} scenes, processing pool size is {}.".format(len(dates), pool_size)
    )
    if pool_size:
        with Pool(pool_size) as p:
            return p.starmap(latest_pixel, dates)
    else:
        for date in dates:
            data.append(retrieve(*latest_pixel))


def composite(
    geojson,
    start,
    end,
    scale,
    bands=["B02", "B03", "B04", "B08", "B8A", "B11", "B12"],
    limit=10,
    clip=False,
    pool=False,
    platform="SENTINEL_2",
    maxcloud=None,
):
    """
    Get the composite over the input features.
    """
    logger.info("Compositing pixels from {} to {}".format(start, end))

    # Check band list.
    BANDS_REQUIRED = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12"]
    missing = [band for band in BANDS_REQUIRED if band not in bands]
    if missing:
        raise ValueError("Missing {} bands for composite.".format(missing))

    required_band_indices = [bands.index(band) for band in BANDS_REQUIRED]

    # Search scenes.
    items = search_data(
        geojson=geojson,
        start=start,
        end=end,
        limit=limit,
        platforms=["SENTINEL_2"],
        maxcloud=maxcloud,
    )

    if not items:
        raise ValueError("No features in search response.")

    stack = None
    creation_args = None
    mask = None
    for item in items:
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
        # Add scene to stack.
        layer = numpy.array([dat[1] for dat in data])
        # Compute cloud mask for new layer.
        layer_clouds = cloud_or_snow_mask(
            *(layer[idx] for idx in required_band_indices)
        )
        # Shadow mask only uses RGB, so limit to first three bands.
        logger.debug(
            "Cloud mask {}".format(numpy.unique(layer_clouds, return_counts=True))
        )
        layer_shades = shadow_mask(*(layer[idx] for idx in required_band_indices[:4]))
        logger.debug(
            "Shade mask {}".format(numpy.unique(layer_shades, return_counts=True))
        )
        layer_clouds = layer_clouds | layer_shades
        logger.debug(
            "Combo mask {}".format(numpy.unique(layer_clouds, return_counts=True))
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
            "Remaining cloud count {}".format(numpy.unique(mask, return_counts=True))
        )
        # If no cloudy pixels are left, stop getting more data.
        if not numpy.any(mask):
            break
    return creation_args, stack
    # Convert stack.
    stack = numpy.array(stack)
    # Compute index of each band in the selection and pass to composite
    # index calculator.
    cidx = composite_index(*(stack[:, idx] for idx in required_band_indices))
    idx1, idx2 = numpy.indices(stack.shape[2:])
    stack = stack[cidx, :, idx1, idx2]
    stack = stack.swapaxes(1, 2).swapaxes(0, 1)
    return creation_args, stack
