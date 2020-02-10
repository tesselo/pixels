import os

from dateutil import parser
from rasterio.features import bounds
from requests import Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.util import Retry

from pixels.const import (
    BASE_SEARCH, PLATFORM_SENTINEL_1, PLATFORM_SENTINEL_2, PREFIX_S1, PREFIX_S2, PRODUCT_L1C, PRODUCT_L2A, QUERY_URL,
    QUERY_URL_MAX_LENGTH, SEARCH_SENTINEL_1, SEARCH_SENTINEL_2, WGS84
)
from pixels.utils import filter_key, geometry_to_wkt, reproject_feature


def search(geom, start, end, platform, product_type, s1_acquisition_mode=None, s1_polarisation_mode=None, max_cloud_cover_percentage=100, raw=False, sort_by_cloud_cover=False):
    """
    Search the scihub for data.
    """
    # Handle Sentinel-1 vs Sentinel-2 case.
    if platform == PLATFORM_SENTINEL_1:
        # Construct extra search key.
        extra = SEARCH_SENTINEL_1.format(sensoroperationalmode=s1_acquisition_mode)
    elif platform == PLATFORM_SENTINEL_2:
        # Convert cloud percentage to integer.
        max_cloud_cover_percentage = int(max_cloud_cover_percentage)
        # Check inputs.
        if max_cloud_cover_percentage < 0 or max_cloud_cover_percentage > 100:
            raise ValueError('Cloud cover percentage out of range [0, 100]'.format(max_cloud_cover_percentage))
        if product_type not in [PRODUCT_L1C, PRODUCT_L2A]:
            raise ValueError('Unknown product type "{}" for Sentinel-2'.format(product_type))
        # Construct extra search key.
        extra = SEARCH_SENTINEL_2.format(cloudcoverpercentage=max_cloud_cover_percentage)

    else:
        raise ValueError('Unknown platform {}'.format(platform))

    # Check geometry and reproject if necessary.
    if geom['type'].capitalize() != 'Feature':
        raise ValueError('Input GeoJson object needs to be of type Feature.')
    if geom['geometry']['type'] not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Input geometry needs to be of type Polygon or MultiPolygon.')
    if 'crs' not in geom:
        raise ValueError('Intput geometry needs an crs specified (for instance "crs": "EPSG:3857").')

    # Transform the geom coordinates into WGS84 for the Scihub search query.
    trsf_geom = reproject_feature(geom, WGS84)

    # For multipolygons, use bounds as search can only be done for polygons. Or
    # if geom query string is too long, use bounds as search argument. Any query
    # of length above 8000 character will fail on scihub. So to be on the safe
    # side, limit the geom only part length. If applicable, convert to bbox.
    if trsf_geom['geometry']['type'] == 'MultiPolygon' or len(str(trsf_geom['geometry']['coordinates']).replace(' ', '')) > QUERY_URL_MAX_LENGTH:
        bnd = bounds(trsf_geom)
        trsf_geom['geometry']['type'] = 'Polygon'
        trsf_geom['geometry']['coordinates'] = [[
            [bnd[0], bnd[1]],
            [bnd[2], bnd[1]],
            [bnd[2], bnd[3]],
            [bnd[0], bnd[3]],
            [bnd[0], bnd[1]],
        ]]

    # Compute WKT for geom.
    geom_wkt = geometry_to_wkt(trsf_geom['geometry'])

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
    # Construct requests session with retries.
    sess = Session()
    sess.mount('https://', HTTPAdapter(max_retries=Retry(total=5, backoff_factor=0.2, status_forcelist=[400, 408, 500, 502, 503, 504, 521, 522, 524])))
    # Get data and convert to dict from json.
    result = sess.get(url, auth=HTTPBasicAuth(os.environ.get('ESA_SCIHUB_USERNAME'), os.environ.get('ESA_SCIHUB_PASSWORD')), verify=False).json()
    # Parse raw data if requested.
    if not raw:
        result = parse_scihub_data(result)

    if sort_by_cloud_cover and not platform == PLATFORM_SENTINEL_1:
        result = sorted(result, key=lambda x: x['max_cloud_cover_percentage'])

    return result


def scihub_entries(data):
    """
    Iterate over entries in this scihub query.
    """
    # If no results were found, return empty list.
    if data['feed']['opensearch:totalResults'] in ['0', None]:
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
            parsed_entry['max_cloud_cover_percentage'] = filter_key(entry, 'double', 'cloudcoverpercentage')

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
