import os

import requests
from dateutil import parser
from pyproj import Proj, transform

from pixels import scihub
from pixels.const import (
    BASE_SEARCH, MODE_EW, MODE_IW, MODE_SM, MODE_WV, PLATFORM_SENTINEL_1, PLATFORM_SENTINEL_2, PREFIX_S1, PREFIX_S2,
    PRODUCT_GRD, PRODUCT_L1C, PRODUCT_L2A, PRODUCT_OCN, PRODUCT_SLC, QUERY_URL, SEARCH_SENTINEL_1, SEARCH_SENTINEL_2,
    WGS84
)
from pixels.utils import filter_key


def search(geom, start, end, platform, product_type, s1_acquisition_mode=None, s1_polarisation_mode=None, s2_max_cloud_cover_percentage=100, raw=False):
    """
    Search the scihub for data.
    """
    # Handle Sentinel-1 vs Sentinel-2 case.
    if platform == PLATFORM_SENTINEL_1:
        # Check inputs.
        if s1_acquisition_mode not in [MODE_SM, MODE_IW, MODE_EW, MODE_WV]:
            raise ValueError('Unknown acquisition mode "{}" for Sentinel-1'.format(s1_acquisition_mode))

        if product_type not in [PRODUCT_GRD, PRODUCT_SLC, PRODUCT_OCN]:
            raise ValueError('Unknown product type "{}" for Sentinel-1'.format(product_type))
        # Construct extra search key.
        extra = SEARCH_SENTINEL_1.format(sensoroperationalmode=s1_acquisition_mode)

    elif platform == PLATFORM_SENTINEL_2:
        # Convert cloud percentage to integer.
        s2_max_cloud_cover_percentage = int(s2_max_cloud_cover_percentage)
        # Check inputs.
        if s2_max_cloud_cover_percentage < 0 or s2_max_cloud_cover_percentage > 100:
            raise ValueError('Cloud cover percentage out of range [0, 100]'.format(s2_max_cloud_cover_percentage))
        if product_type not in [PRODUCT_L1C, PRODUCT_L2A]:
            raise ValueError('Unknown product type "{}" for Sentinel-2'.format(product_type))
        # Construct extra search key.
        extra = SEARCH_SENTINEL_2.format(cloudcoverpercentage=s2_max_cloud_cover_percentage)

    else:
        raise ValueError('Unknown platform {}'.format(platform))

    # Check geometry and reproject if necessary.
    if geom['type'].capitalize() != 'Feature':
        raise ValueError('Input GeoJson object needs to be of type Feature.')
    if geom['geometry']['type'].capitalize() != 'Polygon':
        raise ValueError('Input geometry needs to be of type Polygon.')
    if 'srs' not in geom:
        raise ValueError('Intput geometry needs an srs specified (for instance "srs": "EPSG:3857").')

    # Setup the srs objects for projection.
    src_srs = Proj(init=geom['srs'])
    tar_srs = Proj(init=WGS84)

    # Transform the geom coordinates into WGS84.
    transformed_coords = [transform(src_srs, tar_srs, coord[0], coord[1]) for coord in geom['geometry']['coordinates'][0]]

    # Compute WKT for geom.
    geom_wkt = 'POLYGON(({}))'.format(','.join(['{} {}'.format(*coord) for coord in transformed_coords]))

    # Construct search string.
    search = BASE_SEARCH.format(
        platform=platform,
        product_type=product_type,
        extra=extra,
        geom=geom_wkt,
        start=start,
        end=end,
    )

    # Construct query url.
    url = QUERY_URL.format(search=search)

    # Get data and convert to dict from json.
    result = requests.get(url, auth=requests.auth.HTTPBasicAuth(os.environ.get('ESA_SCIHUB_USERNAME'), os.environ.get('ESA_SCIHUB_PASSWORD')), verify=False).json()

    # Parse raw data if requested.
    if not raw:
        result = parse_scihub_data(result)

    return result


def scihub_entries(data):
    """
    Iterate over entries in this scihub query.
    """
    # If no results were found, return empty list.
    if data['feed']['opensearch:totalResults'] == '0':
        return []
    elif int(data['feed']['opensearch:totalResults']) > int(data['feed']['opensearch:itemsPerPage']):
        print('WARNING: More than 100 results found, result paginated.')
    # Extract entries.
    data = data['feed']['entry']
    # When only result is found, the entry is a dictionary. Convert it to list
    # to unify the data format.
    if isinstance(data, dict):
        data = [data]

    return data


def parse_scihub_data(data):
    """
    Convert scihub results into S3 prefixes matching the same data in the aws
    data repositories.
    """
    result = []
    for entry in scihub_entries(data):
        platform = filter_key(entry, 'str', 'platformname')
        # Convert metadata date string to datetime object.
        date = filter_key(entry, 'date', 'beginposition')
        date = parser.parse(date)
        # Convert metadata footprint string to EWKT object.
        footprint = filter_key(entry, 'str', 'footprint')
        footprint = 'SRID=4326;' + footprint
        # Parse platform specific entry sections.
        if platform == PLATFORM_SENTINEL_1:
            parsed_entry = parse_s1_entry(entry, date)
        else:
            parsed_entry = parse_s2_entry(entry, date)
            # Append scene count for this date and mgrstile to match S3 structure.
            count_duplicates = sum([dat['prefix'][:-2] == parsed_entry['prefix'] for dat in result])
            parsed_entry['prefix'] += '{}/'.format(count_duplicates)

        parsed_entry.update({'date': str(date), 'footprint': footprint})

        result.append(parsed_entry)

    return result


def parse_s1_entry(entry, date):
    """
    Parse a Sentinel-1 scihub data entry.
    """
    title = entry['title'].split('_')
    product_type = filter_key(entry, 'str', 'producttype')
    identifier = filter_key(entry, 'str', 'identifier')
    acquisition_mode = filter_key(entry, 'str', 'sensoroperationalmode')
    polarisation_mode = filter_key(entry, 'str', 'polarisationmode')
    platform_name = filter_key(entry, 'str', 'platformname')
    polarisation_mode = title[3][2:4]

    prefix = PREFIX_S1.format(
        product_type=product_type,
        year=date.year,
        month=date.month,
        day=date.day,
        mode=acquisition_mode,
        polarisation=polarisation_mode,
        product_identifier=identifier,
    )
    return {
        'prefix': prefix, 'polarisation_mode': polarisation_mode,
        'acquisition_mode': acquisition_mode, 'product_type': product_type,
        'platform_name': platform_name, 'polarisation_mode': polarisation_mode,
    }


def parse_s2_entry(entry, date):
    """
    Parse a Sentinel-2 scihub data entry.
    """
    identifier = filter_key(entry, 'str', 'identifier')
    tileid = identifier.split('_')[-2]
    tileid = tileid[1:] if len(tileid) == 6 else tileid
    product_type = filter_key(entry, 'str', 'producttype')
    processing_level = filter_key(entry, 'str', 'processinglevel')
    platform_name = filter_key(entry, 'str', 'platformname')
    # Compute prefix.
    prefix = PREFIX_S2.format(
        product_type=product_type,
        utm=tileid[:2] if len(tileid) == 5 else tileid[:1],
        lz=tileid[-3:-2],
        grid=tileid[-2:],
        year=date.year,
        month=date.month,
        day=date.day,
    )

    return {
        'prefix': prefix, 'mgrs': tileid, 'processing_level': processing_level,
        'platform_name': platform_name,
    }


def pixels(geom, start, end, platform=[PLATFORM_SENTINEL_1, PLATFORM_SENTINEL_2], max_cloud_cover_percentage=100, mode='latest_pixel', scale=10, s2_bands=['B04']):
    """
    {
    'geom': {geojson},
    'start': '2018-12-11',
    'end': '2019-02-14',
    'platform': ['Sentinel-1', 'Sentinel-2', ],
    'max-cloud-cover-percentage': 100,
    'mode': ['query_only', 'latest_pixel', 'composite', 'all_images', ]
    }

    """
    result = {
        'config': {
            'geom': geom,
            'start': start,
            'end': end,
            'platform': platform,
            'max_cloud_cover_percentage': max_cloud_cover_percentage,
        },
    }
    if PLATFORM_SENTINEL_1 in platform:
        dat = {}
        dat['scenes'] = search(
            geom=geom,
            start=start,
            end=end,
            platform=PLATFORM_SENTINEL_1,
            product_type=PRODUCT_GRD,
            s1_acquisition_mode=MODE_IW,
        )
        if mode in ['latest_pixel', 'composite']:  # For sentinel-1 latest pixel and composite are equivalent.
            dat[mode] = scihub.latest_pixel(geom, dat['scenes'], scale=scale)
        elif mode != 'query_only':
            dat['stacks'] = [scihub.get_pixels(geom, entry) for entry in dat['scenes']]

        result[PLATFORM_SENTINEL_1] = dat

    if PLATFORM_SENTINEL_2 in platform:
        dat = {}
        dat['scenes'] = search(
            geom=geom,
            start=start,
            end=end,
            platform=PLATFORM_SENTINEL_2,
            product_type=PRODUCT_L1C,
            s2_max_cloud_cover_percentage=max_cloud_cover_percentage,
        )
        if mode == 'latest_pixel':
            dat[mode] = scihub.latest_pixel(geom, dat['scenes'], scale=scale, bands=s2_bands)
        elif mode != 'query_only':
            dat['stacks'] = [scihub.get_pixels(geom, entry, bands=s2_bands) for entry in dat['scenes']]

        if mode == 'composite':
            dat[mode] = scihub.s2_composite(dat['stacks'])

        result[PLATFORM_SENTINEL_2] = dat

    return result
