import logging
from multiprocessing import Pool

import numpy

from pixels.clouds import composite_index
from pixels.const import LS_BANDS, LS_PLATFORMS, NODATA_VALUE, S2_BANDS
from pixels.retrieve import retrieve
from pixels.search import search_data
from pixels.utils import compute_mask, timeseries_steps

# Get logger
logger = logging.getLogger(__name__)

LANDSAT_1_LAUNCH_DATE = '1972-07-23'


def latest_pixel_s2(geojson, end_date, scale, bands=S2_BANDS, platform='SENTINEL_2', limit=10, clip=False, pool=False, maxcloud=None):
    """
    Get the latest pixel for the input items over the input fetures.
    """
    # Skip search if list of scenes was provided, otherwise assume input is a specific end_date to search with.
    if isinstance(end_date, (list, tuple)):
        logger.info('Latest pixels for {} items.'.format(len(end_date)))
        items = end_date
    else:
        response = search_data(geojson=geojson, start=LANDSAT_1_LAUNCH_DATE, end=end_date, limit=limit, platform=platform, maxcloud=maxcloud)

        if not response:
            raise ValueError('No scenes in search response.')

        # Filter by cloud cover.
        items = response
        if maxcloud is not None:
            items = [item for item in items if item['cloud_cover'] <= maxcloud]

    stack = None
    first_end_date = None
    for item in items:
        logger.info(str(item['product_id']))
        # Track first end date (highest priority image in stack).
        if first_end_date is None:
            first_end_date = str(items[0]['sensing_time'].date())
        # Prepare band list.
        band_list = [(item['bands'][band], geojson, scale, False, False, False, None)for band in bands]

        if pool:
            with Pool(len(bands)) as p:
                data = p.starmap(retrieve, band_list)
        else:
            data = []
            for band in band_list:
                data.append(retrieve(*band))

        # Create stack.
        mask = None
        if stack is None:
            # Set first return as stack.
            stack = [dat[1] for dat in data]
            # Extract creation arguments.
            creation_args = data[0][0]
        else:
            # Update nodata values in stack with new pixels.
            for i in range(len(bands)):
                stack[i][mask] = data[i][1][mask]

        # Compute nodata mask.
        mask = stack[0] == NODATA_VALUE

        # If all pixels were populated stop getting more data.
        if not numpy.any(mask):
            break

    # Clip stack to geometry if requested.
    if clip:
        mask = compute_mask(
            geojson,
            creation_args['height'],
            creation_args['width'],
            creation_args['transform'],
        )
        for i in range(len(stack)):
            stack[i][mask] = NODATA_VALUE

    return creation_args, first_end_date, stack


def latest_pixel_s2_stack(geojson, start, end, scale, interval='weeks', bands=None, platforms='SENTINEL_2', limit=10, clip=False, maxcloud=None):
    """
    Get the latest pixel at regular intervals between two dates.
    """
    # Check if is list or tuple
    if not isinstance(platforms, (list, tuple)):
        platforms = (platforms)

    retrieve_pool = False

    if interval == 'all':
        # Get all scenes of for this date range.
        response = search_data(geojson=geojson, start=start, end=end, limit=limit, platform=platforms, maxcloud=maxcloud)

        if not response:
            raise ValueError('No scenes in search response.')

        # Filter by cloud cover.
        items = response
        if maxcloud is not None:
            items = [item for item in items if item['cloud_cover'] <= maxcloud]

        logger.info('Getting {} scenes for this geom.'.format(len(items)))

        limit = 5
        dates = [(geojson, [item], scale, bands, platforms, limit, clip, retrieve_pool, maxcloud) for item in items]
    else:
        # Construct array of latest pixel calls with varying dates.
        dates = [(geojson, step[1], scale, bands, platforms, limit, clip, retrieve_pool, maxcloud) for step in timeseries_steps(start, end, interval)]
        logger.info('Getting {} {} for this geom.'.format(len(dates), interval))

    # Call pixels calls asynchronously.
    pool_size = min(len(dates), 10)
    logger.info('Found {} scenes, processing pool size is {}.'.format(len(dates), pool_size))
    with Pool(pool_size) as p:
        return p.starmap(latest_pixel_s2, dates)


def composite(geojson, start, end, scale, bands=S2_BANDS, limit=10, clip=False, pool=False, platform='SENTINEL_2', maxcloud=None):
    """
    Get the composite over the input features.
    """
    logger.info('Compositing pixels for {}'.format(start))

    response = search_data(geojson=geojson, platform=platform, start=start, end=end, limit=limit, maxcloud=maxcloud)

    if 'bands' not in response:
        raise ValueError('No features in search response.')

    stack = []
    creation_args = None

    for item in response:
        # Prepare band list.
        band_list = [(response['bands'][band], geojson, scale, False, False, False, None)for band in bands]

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
        stack.append(numpy.array([dat[1] for dat in data]))
    # Convert stack.
    stack = numpy.array(stack)
    # Compute index of each band in the selection and pass to composite
    # index calculator.
    BANDS_REQUIRED = ('B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12')
    cidx = composite_index(*(stack[:, bands.index(band)] for band in BANDS_REQUIRED))
    idx1, idx2 = numpy.indices(stack.shape[2:])
    return creation_args, stack[cidx, :, idx1, idx2]
