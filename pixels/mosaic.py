import logging
from multiprocessing import Pool

import numpy
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from pixels.clouds import composite_index
from pixels.const import NODATA_VALUE, S2_BANDS, SEARCH_ENDPOINT
from pixels.retrieve import retrieve
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


def latest_pixel_s2(geojson, date, scale, bands=S2_BANDS, limit=10, clip=False, pool=False, max_cloud_cover=None):
    """
    Get the latest pixel for the input items over the input fetures.
    """
    # Skip search if list of scenes was provided, otherwise assume input is a
    # specific date to search with.
    if isinstance(date, (list, tuple)):
        logger.info('Latest pixels for {} item.'.format(len(date)))
        items = date
    else:
        logger.info('Latest pixels for {}'.format(date))
        search = {
            "intersects": compute_wgs83_bbox(geojson),
            "datetime": "1972-07-23/{}".format(date),  # Landsat 1 launch date.
            "collections": ['sentinel-s2-l2a-cogs'],
            "limit": limit,
        }
        response = http.post(SEARCH_ENDPOINT, json=search)
        response.raise_for_status()
        response = response.json()

        if 'features' not in response:
            raise ValueError('No scenes in search response.')

        # Filter by cloud cover.
        items = response['features']
        if max_cloud_cover is not None:
            items = [item for item in items if item['properties']['eo:cloud_cover'] <= max_cloud_cover]

    stack = None
    for item in items:
        # Prepare band list.
        band_list = [(item['assets'][band]['href'], geojson, scale, False, False, False, None) for band in bands]

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

    return creation_args, date, stack


def latest_pixel_s2_stack(geojson, min_date, max_date, scale, interval='weeks', bands=S2_BANDS, limit=10, clip=False, pool=False, max_cloud_cover=None):
    """
    Get the latest pixel at regular intervals between two dates.
    """
    if interval == 'all':
        # Get all scenes of for this date range.
        search = {
            "intersects": compute_wgs83_bbox(geojson),
            "datetime": "{}/{}".format(min_date, max_date),
            "collections": ['sentinel-s2-l2a-cogs'],
            "limit": 1000,
        }
        response = http.post(SEARCH_ENDPOINT, json=search)
        response.raise_for_status()
        response = response.json()

        if 'features' not in response:
            raise ValueError('No scenes in search response.')

        # Filter by cloud cover.
        items = response['features']
        if max_cloud_cover is not None:
            items = [item for item in items if item['properties']['eo:cloud_cover'] <= max_cloud_cover]

        logger.info('Getting {} scenes for this geom.'.format(len(items)))

        limit = 5
        dates = [(geojson, [item], scale, bands, limit, clip, pool) for item in items]
    else:
        # Construct array of latest pixel calls with varying dates.
        dates = [(geojson, step[1], scale, bands, limit, clip, pool, max_cloud_cover) for step in timeseries_steps(min_date, max_date, interval)]

    # Call pixels calls asynchronously.
    with Pool(len(dates)) as p:
        return p.starmap(latest_pixel_s2, dates)


def composite(geojson, start, end, scale, bands=S2_BANDS, limit=10, clip=False, pool=False):
    """
    Get the composite over the input features.
    """
    logger.info('Compositing pixels for {}'.format(start))

    search = {
        "intersects": compute_wgs83_bbox(geojson),
        "datetime": "{}/{}".format(start, end),  # Landsat 1 launch date.
        "collections": ['sentinel-s2-l2a-cogs'],
        "limit": limit,
    }
    response = http.post(SEARCH_ENDPOINT, json=search)
    response.raise_for_status()
    response = response.json()

    if 'features' not in response:
        raise ValueError('No features in search response.')

    print('Found {} input scenes.'.format(len(response['features'])))##
    print('Cloud cover is {}.'.format([dat['properties']['eo:cloud_cover'] for dat in response['features']]))##

    stack = []
    creation_args = None
    for item in response['features']:
        # Prepare band list.
        band_list = [(item['assets'][band]['href'], geojson, scale, False, False, False, None) for band in bands]

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
