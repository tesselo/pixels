import datetime

import numpy
import sentry_sdk
from rasterio.errors import RasterioIOError
from rasterio.features import sieve

from pixels import tio
from pixels.const import (
    DISCRETE_BANDS,
    LANDSAT_1_LAUNCH_DATE,
    MAX_COMPOSITE_BAND_WORKERS,
    NODATA_VALUE,
    SCENE_CLASS_RANK_FLAT,
    SCL_COMPOSITE_CLOUD_BANDS,
)
from pixels.exceptions import PixelsException
from pixels.log import log_function, logger
from pixels.retrieve import retrieve
from pixels.search import search_data
from pixels.utils import compute_mask, run_concurrently, timeseries_steps
from pixels.validators import (
    CompositeMethodOption,
    ConcurrencyOption,
    LandsatBandOption,
    ModeOption,
    PixelsConfigValidator,
    PixelsSearchValidator,
    PlatformOption,
    SearchOrderOption,
    Sentinel2BandOption,
    SentinelLevelOption,
    TimeStepOption,
)


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


def first_valid_pixel(
    geojson,
    end_date,
    scale,
    bands=None,
    platforms=None,
    limit=10,
    clip=False,
    pool_bands=False,
    maxcloud=None,
    level=None,
    start_date=None,
    sort="sensing_time",
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
    pool_bands : boolean, optional
        If True, thread pooling is used to request the image bands data.
    maxcloud : int, optional
        Maximum accepted cloud coverage in images. If not provided returns records with
        up to 100% cloud coverage.
    level : str, optional
        The level of image processing for Sentinel-2 satellite. It can be 'L1C'(Level-1C)
        or 'L2A'(Level-2A) that provides Bottom Of Atmosphere (BOA) reflectance images
        derived from associated Level-1C products. Ignored if platforms is not Sentinel 2.
    start_date : str, datetime, optional
        A parseable date or datetime string. Represents the starting date of the
        input imagery. Only images after that date will be used for creating
        the output. Example "2020-12-1". The default is 31 days before start_date
        when start_date is not an array or a dictionary, in that case it will be
        LANDSAT_1_LAUNCH_DATE.
    sort : str, optional
        The order of the imagery to find the first valid pixel. Either `sensing_time`
        or `cloud_cover`.

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
            PixelsSearchValidator(
                geojson=geojson,
                start=start_date,
                end=end_date,
                limit=limit,
                platforms=platforms,
                maxcloud=maxcloud,
                level=level,
                bands=bands,
                sort=sort,
            )
        )
        # Return early if no items could be found.
        if not items:
            logger.info(
                "No scenes in search response.",
                funk="first_valid_pixel",
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
        logger.debug(f"Processing item {item['id']}")
        # Track first end date (the highest priority image in stack).
        if first_end_date is None:
            first_end_date = str(items[0]["sensing_time"].date())
        # Prepare band list.
        band_list = []
        for band in bands:
            if band not in item["bands"]:
                raise PixelsException(
                    f"Latest pixel requested for a band not present: {band} in {item['id']}"
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
        if pool_bands:
            try:
                data = run_concurrently(
                    retrieve,
                    variable_arguments=band_list,
                    concurrency=ConcurrencyOption.threading,
                    n_jobs=len(bands),
                )
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
            logger.warning(f"Failed retrieval of bands for {item['id']}, continuing.")
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


def configure_pixel_stack(
    geojson,
    start,
    end,
    scale,
    interval=TimeStepOption.weeks,
    interval_step=1,
    bands=None,
    platforms=PlatformOption.sentinel_2,
    limit=100,
    clip=False,
    maxcloud=None,
    pool_bands=False,
    level=None,
    mode=ModeOption.latest_pixel,
    composite_method=Sentinel2BandOption.scl,
):
    """
    Get the configurations and select function to use.
    """
    # Check if is list or tuple
    if not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    if mode == ModeOption.all or interval == TimeStepOption.all:
        # For all mode, the date range is constructed around each scene, and
        # then latest pixel is used for each date. This way, latest pixel will
        # only have one possible input every time.
        collect = first_valid_pixel
        # Get all scenes of for this date range.
        response = search_data(
            PixelsSearchValidator(
                geojson=geojson,
                start=start,
                end=end,
                limit=limit,
                platforms=platforms,
                maxcloud=maxcloud,
                level=level,
                bands=bands,
            )
        )

        if not response:
            logger.info(
                "No scenes in search response.",
                funk="pixel_stack",
                search_date_end=end,
                search_date_start=start,
            )
            return None, None, None

        logger.info(f"Getting {len(response)} scenes for this stack.")

        configs = [
            (
                geojson,
                [item],
                scale,
                bands,
                platforms,
                limit,
                clip,
                pool_bands,
                maxcloud,
                level,
            )
            for item in response
        ]
    elif mode in [ModeOption.latest_pixel, ModeOption.cloud_sorted_pixel]:
        collect = first_valid_pixel
        if mode == ModeOption.latest_pixel:
            sort = SearchOrderOption.sensing_time
        else:
            sort = SearchOrderOption.cloud_cover
        # Construct array of latest pixel calls with varying dates.
        configs = [
            (
                geojson,
                step[1],
                scale,
                bands,
                platforms,
                limit,
                clip,
                pool_bands,
                maxcloud,
                level,
                step[0],
                sort,
            )
            for step in timeseries_steps(start, end, interval, interval_step)
        ]
    elif mode == ModeOption.composite:
        collect = composite
        sort = SearchOrderOption.cloud_cover
        finish_early_cloud_cover_percentage = 0.05
        # Create input list with date ranges.
        configs = [
            (
                geojson,
                step[0],
                step[1],
                scale,
                bands,
                limit,
                clip,
                pool_bands,
                maxcloud,
                level,
                sort,
                finish_early_cloud_cover_percentage,
                platforms,
                composite_method,
            )
            for step in timeseries_steps(start, end, interval, interval_step)
        ]

    if mode != ModeOption.all:
        logger.info(f"Getting {len(configs)} {interval} {mode} images for this stack.")

    return collect, configs


def process_search_images(collect, search):
    """
    Run the search for each image.

    Parameters
    ----------
        collect : function
            Funtion to use for collecting.
        search : dict
            Configuration for searching and collecting images.

    Returns
    -------
    creation_args : dict or None
        The creation arguments metadata for the extracted pixel matrix. Can be
        used to write the extracted pixels to a file if desired.
    dates : date object or None
        The date of the first scene used to create the output image.
    pixels : numpy array or None
        The extracted pixel stack, with shape (bands, height, width).
    """
    result = collect(*search)
    if result[2] is None:
        return None, None, None
    # Remove results that are all nodata.
    if numpy.all(result[2][0] == NODATA_VALUE):
        return None, None, None
    # Convert to individual arrays.
    creation_args = result[0]
    dates = result[1]
    pixels = numpy.array(result[2])
    return creation_args, dates, pixels


def fetch_write_images(search, collect, out_path):
    """
    Collect the images, write them to disk

    Parameters
    ----------
        search : dict
            Configuration for searching and collecting images.
        collect : function
            Funtion to use for collecting.
        out_path : str
            Path to folder containing the item's images.
    Returns
    -------
        out_path_date : str
            Path to saved raster.
    """
    meta, dates, pixels = process_search_images(collect, search)
    # Return early if no results are left after cleaning.
    parameter_missing = [True for f in (meta, dates, pixels) if f is None]
    if any(parameter_missing):
        logger.info(
            "No scenes in search response.",
            funk="pixel_stack",
            search_date_end=dates,
            search_config=search,
        )
        return None
    return tio.write_tiff_from_pixels_stack(dates, pixels, out_path, meta)


@log_function
def pixel_stack(
    geojson,
    start,
    end,
    scale,
    interval=TimeStepOption.weeks,
    interval_step=1,
    bands=None,
    platforms=PlatformOption.sentinel_2,
    limit=100,
    clip=False,
    maxcloud=None,
    pool_size=5,
    pool_bands=False,
    level=None,
    mode=ModeOption.latest_pixel,
    composite_method=Sentinel2BandOption.scl,
    out_path="",
):
    """
    Get the images at regular intervals between two dates.
    """
    collect, search_configurations = configure_pixel_stack(
        geojson,
        start,
        end,
        scale,
        interval=interval,
        interval_step=interval_step,
        bands=bands,
        platforms=platforms,
        limit=limit,
        clip=clip,
        maxcloud=maxcloud,
        pool_bands=pool_bands,
        level=level,
        mode=mode,
        composite_method=composite_method,
    )
    # Get pixels.
    pool_size = min(len(search_configurations), pool_size)
    logger.info(f"Processing pool size is {pool_size}.")
    raster_list = []
    if pool_size > 1:
        raster_list = run_concurrently(
            fetch_write_images,
            variable_arguments=search_configurations,
            static_arguments=[collect, out_path],
            concurrency=ConcurrencyOption.threading,
            n_jobs=pool_size,
        )
    else:
        for search in search_configurations:
            raster_list.append(fetch_write_images(search, collect, out_path))
    return raster_list


def retrieve_item_bands(
    item: dict, geojson: dict, scale: float, bands: list, pool_bands: bool
) -> tuple:
    """
    Get pixels for a search result item.

    Parameters
    ----------
    item : dict
        Pxsearch search result item.
    geojson : dict
        The geographic area in geojson format for which to retrieve imagery.
    scale : float
        The resolution of the output data in same the CRS as the geojson input.
    bands : list
        Band names of all the bands that should be retrieved for this item.
    pool_bands : bool
        Determine if a thread pool should be used for retrieving the data.


    Returns
    -------
    creation_args : dict or None
        The creation arguments metadata for the extracted pixel matrix. Can be
        used to write the extracted pixels to a file if desired.
    stack : numpy array or None
        The extracted pixel stack, with shape (bands, height, width).
    """
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
        for band in bands
    ]

    if pool_bands:
        max_workers = min(MAX_COMPOSITE_BAND_WORKERS, len(band_list))
        data = run_concurrently(
            retrieve,
            variable_arguments=band_list,
            concurrency=ConcurrencyOption.threading,
            n_jobs=max_workers,
        )
    else:
        data = []
        for band in band_list:
            data.append(retrieve(*band))

    creation_args = data[0][0]
    pixels_arrays = numpy.array([dat[1] for dat in data])

    return creation_args, pixels_arrays


def get_composite_items(
    input: PixelsConfigValidator, sort: bool, composite_method: CompositeMethodOption
):
    """
    Yield all items required for composites.
    """
    if (
        composite_method in (CompositeMethodOption.scl, CompositeMethodOption.full)
        and Sentinel2BandOption.scl not in input.bands
    ):
        bands = list(input.bands) + [Sentinel2BandOption.scl.value]
    elif (
        composite_method == CompositeMethodOption.qa_pixel
        and LandsatBandOption.qa_pixel not in input.bands
    ):
        bands = list(input.bands) + [LandsatBandOption.qa_pixel.value]
    else:
        bands = input.bands

    items = search_data(
        PixelsSearchValidator(
            geojson=input.geojson,
            start=input.start,
            end=input.end,
            maxcloud=input.maxcloud,
            limit=input.limit,
            level=input.level,
            platforms=input.platforms,
            bands=bands,
            sort=sort,
        )
    )

    if not items:
        logger.info(
            "No scenes in search response.",
            funk="composite",
            search_date_end=input.end,
            search_date_start=input.start,
        )

    for item in items:
        creation_args, layer = retrieve_item_bands(
            item, input.geojson.dict(), input.scale, bands, input.pool_bands
        )
        if any(band is None for band in layer):
            continue
        end_date = str(item["sensing_time"].date())

        yield creation_args, end_date, layer


def composite(
    geojson,
    start,
    end,
    scale,
    bands,
    limit=10,
    clip=False,
    pool_bands=False,
    maxcloud=None,
    level=SentinelLevelOption.l2a,
    sort=SearchOrderOption.cloud_cover,
    finish_early_cloud_cover_percentage=0.05,
    platforms=PlatformOption.sentinel_2,
    composite_method=CompositeMethodOption.scl,
):
    """
    Get the composite over the input features.
    """
    logger.info(f"Compositing pixels from {start} to {end}")
    input = PixelsConfigValidator(
        geojson=geojson,
        start=start,
        end=end,
        scale=scale,
        bands=bands,
        limit=limit,
        clip=clip,
        pool_bands=pool_bands,
        maxcloud=maxcloud,
        level=level,
        platforms=platforms,
        mode=ModeOption.composite,
        composite_method=composite_method,
    )

    if composite_method in (
        CompositeMethodOption.scl,
        CompositeMethodOption.full,
    ) and Sentinel2BandOption.scl in list(input.bands):
        cloud_band_index = input.bands.index(Sentinel2BandOption.scl)
    elif (
        composite_method == CompositeMethodOption.qa_pixel
        and LandsatBandOption.qa_pixel in list(input.bands)
    ):
        cloud_band_index = input.bands.index(LandsatBandOption.qa_pixel)
    else:
        # Cloud class band will be added at the end of the list if its not present.
        cloud_band_index = -1

    stack = None
    creation_args = None
    mask = None
    first_end_date = None

    for new_creation_args, new_end_date, layer in get_composite_items(
        input, sort, composite_method
    ):
        if first_end_date is None:
            first_end_date = new_end_date

        if creation_args is None:
            creation_args = new_creation_args

        layer_clouds = None

        if composite_method == CompositeMethodOption.scl:
            layer_clouds = numpy.isin(
                layer[cloud_band_index], SCL_COMPOSITE_CLOUD_BANDS
            )
        elif composite_method == CompositeMethodOption.qa_pixel:
            qa = layer[cloud_band_index]
            # Bit 1 is dilated cloud, 3 is cloud, 4 is cloud shadow.
            nodata_byte = numpy.array(1 << 0, dtype=qa.dtype)
            dilated_cloud_byte = numpy.array(1 << 1, dtype=qa.dtype)
            cloud_byte = numpy.array(1 << 3, dtype=qa.dtype)
            shadow_byte = numpy.array(1 << 4, dtype=qa.dtype)

            nodata_mask = numpy.bitwise_and(qa, nodata_byte)
            dilated_cloud = numpy.bitwise_and(qa, dilated_cloud_byte)
            cloud = numpy.bitwise_and(qa, cloud_byte)
            shadow = numpy.bitwise_and(qa, shadow_byte)

            layer_clouds = (dilated_cloud | cloud | shadow | nodata_mask).astype(
                dtype="bool"
            )
            # The landsat cloud mask has lots of 1 or 2 pixel speckles should can
            # be removed to improve quality of output.
            if layer_clouds.size > 3:
                layer_clouds = sieve(layer_clouds.astype("uint8"), 3).astype("bool")
        elif composite_method == CompositeMethodOption.full:
            # Use SCL layer to select pixel ranks.
            cloud_probs = numpy.choose(
                layer[cloud_band_index], SCENE_CLASS_RANK_FLAT
            ).astype("float")

            # Compute NDVI, avoiding zero division.
            B4 = layer[input.bands.index(Sentinel2BandOption.b4)].astype("float")
            B8 = layer[input.bands.index(Sentinel2BandOption.b8)].astype("float")
            ndvi_diff = B8 - B4
            ndvi_sum = B8 + B4
            ndvi_sum[ndvi_sum == 0] = 1
            ndvi = ndvi_diff / ndvi_sum

            # Add inverted and scaled NDVI values to the decimal range of the cloud
            # probs. This ensures that within acceptable pixels, the one with the
            # highest NDVI is selected.
            scaled_ndvi = (1 - ndvi) / 100
            cloud_probs += scaled_ndvi
            if stack is None:
                stack = []
            stack.append((layer, cloud_probs))
            continue

        logger.debug(
            "Layer masked count {} %".format(
                int(100 * numpy.sum(layer_clouds) / layer_clouds.size)
            )
        )
        if stack is None:
            stack = layer
            mask = layer_clouds
        else:
            # Update cloudy values in stack with new pixels, but only if the
            # new pixels are not nodata.
            layer_data_mask = layer[0] != NODATA_VALUE
            local_update_mask = mask & layer_data_mask
            for i in range(stack.shape[0]):
                stack[i][local_update_mask] = layer[i][local_update_mask]

            mask = mask & layer_clouds

        logger.debug(
            "Remaining masked count {} %".format(int(100 * numpy.sum(mask) / mask.size))
        )

        if numpy.sum(stack[0] == NODATA_VALUE):
            logger.debug("There are remaining NA values continuing compositing")
            continue
        elif numpy.sum(mask) / mask.size <= finish_early_cloud_cover_percentage:
            logger.debug("Very little clouds left, finalizing compositing early.")
            break

    if stack is None:
        return None, None, None

    if composite_method == CompositeMethodOption.full:
        # Compute an array of scene indices with the lowest cloud probability.
        cloud_probs = [scene[1] for scene in stack]
        selector_index = numpy.argmin(cloud_probs, axis=0)
        band_count = stack[0][0].shape[0]
        result = []
        for index in range(band_count):
            # Merge scene tiles for this band into a composite tile using the selector index.
            bnds = numpy.array([dat[0][index] for dat in stack])
            # Construct final composite band array from selector index.
            idx1, idx2 = numpy.indices(
                (creation_args["height"], creation_args["width"])
            )
            # Create the composite from the scens using index magic.
            result.append(bnds[selector_index, idx1, idx2])
        stack = numpy.array(result)

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

    # Remove scl if required.
    if (
        composite_method in (CompositeMethodOption.scl, CompositeMethodOption.full)
        and Sentinel2BandOption.scl not in input.bands
    ) or (
        composite_method == CompositeMethodOption.qa_pixel
        and LandsatBandOption.qa_pixel not in input.bands
    ):
        stack = numpy.delete(stack, cloud_band_index, 0)

    return creation_args, first_end_date, numpy.array(stack)
