import logging
from multiprocessing import Pool

import numpy
import requests
from rasterio.features import bounds
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from pixels.clouds import composite_index
from pixels.const import NODATA_VALUE, S2_BANDS, SEARCH_ENDPOINT
from pixels.retrieve import retrieve
from pixels.search_img import get_bands, search_data
from pixels.utils import compute_mask, compute_wgs83_bbox, timeseries_steps

# Get logger
logger = logging.getLogger(__name__)

# Instanciate requests retry strategy.
retry_strategy = Retry(
    total=5,
    status_forcelist=[413, 429, 500, 502, 503, 504],
    method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
    backoff_factor=1,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

LANDSAT_1_LAUNCH_DATE = '1972-07-23'

def latest_pixel_s2(geojson, end_date, scale, bands=S2_BANDS, platform='SENTINEL_2', limit=10, clip=False, pool=False, maxcloud=None):
    """
    Get the latest pixel for the input items over the input fetures.
    """
    # Skip search if list of scenes was provided, otherwise assume input is a specific end_date to search with.
    if isinstance(end_date, (list, tuple)):
        logger.info('Latest pixels for {} item.'.format(len(end_date)))
        items = end_date
    else:
        response = get_bands(search_data(geojson=geojson, start=LANDSAT_1_LAUNCH_DATE, end=end_date, limit=limit, platform=platform, maxcloud=maxcloud))

        if  not response:
            raise ValueError('No scenes in search response.')

        # Filter by cloud cover.
        items = response
        if maxcloud is not None:
            items = [item for item in items if item['cloud_cover'] <= maxcloud]

    stack = None

    for item in items:
        logger.info(str(item['product_id']))
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

    return creation_args, stack


def latest_pixel_s2_stack(geojson, end, scale, interval='weeks', bands=S2_BANDS, platform='SENTINEL_2', limit=10, clip=False, pool=False, maxcloud=None):
    """
    Get the latest pixel at regular intervals between two dates.
    """
    if interval == 'all':
        # Get all scenes of for this date range.
        response = get_bands(search_data(geojson=geojson, start=LANDSAT_1_LAUNCH_DATE, end=end, limit=limit, platform=platform, maxcloud=maxcloud))

        if 'bands' not in response:
            raise ValueError('No scenes in search response.')

        # Filter by cloud cover.
        items = response
        if maxcloud is not None:
            items = [item for item in items if item['cloud_cover'] <= maxcloud]

        logger.info('Getting {} scenes for this geom.'.format(len(items)))

        limit = 5
        dates = [(geojson, [item], scale, bands, limit, clip, pool) for item in items]
    else:
        # Construct array of latest pixel calls with varying dates.
        dates = [(geojson, step[1], scale, bands, limit, clip, pool, maxcloud) for step in timeseries_steps(start, end, interval)]
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

    response = get_bands(search_data(geojson=geojson, platform=platform, start =start, end=end, limit=limit, maxcloud=maxcloud))

    if 'bands' not in response:
        raise ValueError('No features in search response.')

    print('Found {} input scenes.'.format(len(response)))##
    print('Cloud cover is {}.'.format([dat['cloud_cover'] for dat in response]))##

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
