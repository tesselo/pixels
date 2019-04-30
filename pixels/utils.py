import glob
import logging
import os
import uuid
from copy import deepcopy
from io import BytesIO
from math import ceil, pi

import numpy
import rasterio
from dateutil import parser
from flask import send_file
from PIL import Image
from pyproj import Proj, transform
from rasterio import Affine
from rasterio.features import bounds, rasterize
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from pixels import const
from pixels.exceptions import PixelsFailed

logger = logging.getLogger(__name__)


def generate_unique_key(frmt, ts_tag=''):
    """
    Generate a unique S3 file key to upload files to.
    """
    if ts_tag:
        ts_tag = '{}/'.format(ts_tag)

    return '{}{}/pixels.{}'.format(
        ts_tag,
        uuid.uuid4(),
        frmt.lower(),
    )


def filter_key(entry, namespace, key):
    """
    Extract a value from a section of a scihub entry namespace.
    """
    search_target = entry[namespace]
    if isinstance(search_target, dict):
        search_target = [search_target]
    return list(filter(lambda d: d['name'] == key, search_target))[0]['content']


def compute_transform(geom, scale):
    """
    Compute warp parameters from geometry. The scale is expected to be in the
    coordinate system units of the geometry.
    """
    extent = bounds(geom)
    transform = Affine(scale, 0, extent[0], 0, -scale, extent[3])
    width = ceil((extent[2] - extent[0]) / scale)
    height = ceil((extent[3] - extent[1]) / scale)

    return transform, width, height, geom['crs']


def tile_scale(z):
    """
    Calculate tile pixel size scale for given zoom level.
    """
    TILESIZE = 256
    WEB_MERCATOR_WORLDSIZE = 2 * pi * 6378137
    scale = WEB_MERCATOR_WORLDSIZE / 2.0 ** z / TILESIZE
    return round(scale, 8)


def warp_from_s3(bucket, prefix, transform, width, height, crs):
    """
    Warp a raster from S3 onto a local target raster using the target geotransform.
    """
    # Construct vsi path for the prefix.
    vsis3path = '/vsis3/{bucket}/{prefix}'.format(
        bucket=bucket,
        prefix=prefix,
    )

    # Open remote raster.
    with rasterio.open(vsis3path) as src:
        # Prepare creation parameters for memory raster.
        creation_args = src.meta.copy()
        creation_args.update({
            'driver': 'GTiff',
            'crs': crs,
            'transform': transform,
            'width': width,
            'height': height,
        })
        # Open memory destination file.
        memfile = MemoryFile()
        dst = memfile.open(**creation_args)
        # Prepare projection arguments.
        proj_args = {
            'dst_transform': transform,
            'dst_crs': crs,
            'resampling': Resampling.nearest,
        }

        if src.crs:
            # Extract source crs directly.
            src_crs = src.crs
        else:
            # Extract georeference points and source crs from gcps.
            src_gcps, src_crs = src.gcps
            proj_args['gcps'] = src.gcps[0]

        # Set source crs.
        proj_args['src_crs'] = src_crs

        # Transform raster bands from source to destination.
        for i in range(1, src.count + 1):
            proj_args.update({
                'src_crs': src_crs,
                'source': rasterio.band(src, i),
                'destination': rasterio.band(dst, i),
            })
            reproject(**proj_args)

        # Return memfile.
        memfile.seek(0)
        return memfile


def write_to_disk(rst, path):
    """
    Write a memory raster to disk.
    """
    with rasterio.open(path, 'w', **rst.meta.copy()) as dst:
        dst.write(rst.read())


def clone_raster(rst, data):
    """
    Clone a raster.
    """
    # Clone raster.
    creation_args = rst.meta.copy()
    memfile = MemoryFile()
    dst = memfile.open(**creation_args)

    # Write band data to target raster.
    dst.write(data.reshape((1, ) + (rst.height, rst.width)))

    # Return memfile object.
    return memfile


def persist(entry, folder):
    """
    Persist pixel data from an entry to a folder.
    """
    for band, val in entry['pixels'].items():
        write_to_disk(val, os.path.join(folder, '{}-{}-{}.tif'.format(entry['mgrs'], entry['date'].date(), band)))


def load_stacks(folder):
    """
    Load all persisted stacks from this folder.
    """
    stacks = {}
    for path in glob.glob(os.path.join(folder, '*.tif')):
        # mgrs, year, month, day, band = os.path.basename(path).split('.tif')[0].split('-')
        band, year, month, day, mgrs = os.path.basename(path).split('.tif')[0].split('-')
        key = '{}-{}-{}-{}'.format(mgrs, year, month, day)
        if key not in stacks:
            stacks[key] = {}
        stacks[key][band] = rasterio.open(path, 'r')
    return stacks


def tile_bounds(z, x, y):
    """
    Calculate the bounding box of a specific tile.
    """
    WEB_MERCATOR_WORLDSIZE = 2 * pi * 6378137

    WEB_MERCATOR_TILESHIFT = WEB_MERCATOR_WORLDSIZE / 2.0

    zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

    xmin = x * zscale - WEB_MERCATOR_TILESHIFT
    xmax = (x + 1) * zscale - WEB_MERCATOR_TILESHIFT
    ymin = WEB_MERCATOR_TILESHIFT - (y + 1) * zscale
    ymax = WEB_MERCATOR_TILESHIFT - y * zscale

    return [xmin, ymin, xmax, ymax]


def clip_to_geom(stack, geom):
    """
    Clip all rasters in this stack to the geometry.
    """
    # Compute mask from geom.
    with next(iter(stack.values())).open() as rst:
        mask = rasterize([geom['geometry']], out_shape=rst.shape, transform=rst.transform, all_touched=True).astype('bool')
    # If all pixels were included, return early.
    if numpy.all(mask):
        return stack
    # Invert mask to use for clipping rasters.
    mask = numpy.logical_not(mask)
    # Mask all rasters.
    result = {}
    for key, val in stack.items():
        with val.open() as rst:
            dat = rst.read(1)
            dat[mask] = const.SENTINEL_2_NODATA
            dat = dat.reshape((1, ) + dat.shape)
            result[key] = clone_raster(rst, dat)

    return result


def get_empty_tile():
    """
    Tesselo + symbol as default.
    """
    path = os.path.dirname(os.path.abspath(__file__))
    img = Image.open(os.path.join(path, 'assets/tesselo_empty.png'))
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return send_file(
        output,
        mimetype='image/png'
    )


def reproject_coords(coords, src, tar):
    """
    Reproject a list of polygon coordinates.
    """
    transformed_coords = []

    if len(coords) > 1:
        raise ValueError('Polygons with interior rings are not supported.')

    for coord in coords[0]:
        transformed_coords.append(transform(src, tar, coord[0], coord[1]))

    return [transformed_coords]


def reproject_feature(feature, target_crs):
    """
    Reproject Polygon and MultiPolygon GeoJson objects.
    """
    feat = deepcopy(feature)
    src = Proj(init=feat['crs'])
    tar = Proj(init=target_crs)

    feat['crs'] = target_crs

    if feat['geometry']['type'] == 'MultiPolygon':
        trsf = []
        for poly in feat['geometry']['coordinates']:
            trsf.append(reproject_coords(poly, src, tar))
        feat['geometry']['coordinates'] = trsf
    elif feat['geometry']['type'] == 'Polygon':
        feat['geometry']['coordinates'] = reproject_coords(feat['geometry']['coordinates'], src, tar)
    else:
        raise ValueError('Geometry type "{}" is not supported. Please use Polygon or MultiPolygon.')

    return feat


def geometry_to_wkt(geom):
    """
    Convert a Polygon or MultiPolygon to WKT.
    """
    if geom['type'] == 'Polygon':
        if len(geom['coordinates']) > 1:
            raise ValueError('Polygons with interior rings are not supported.')
        return 'POLYGON(({}))'.format(','.join(['{} {}'.format(*coord) for coord in geom['coordinates'][0]]))
    elif geom['type'] == 'MultiPolygon':
        wkt = ''
        for poly in geom['coordinates']:
            if len(poly) > 1:
                raise ValueError('Polygons with interior rings are not supported.')
            wkt += '(({}))'.format(','.join(['{} {}'.format(*coord) for coord in poly[0]]))
        return 'MULTIPOLYGON({})'.format(wkt)
    else:
        raise ValueError('Geometry type "{}" is not supported. Please use Polygon or MultiPolygon.')


def validate_configuration(config):
    """
    Returns a validated configuration.
    """
    # Remove auth key from config dict.
    config.pop('key', None)

    # Transform the geom coordinates into web mercator and limit size.
    trsf_geom = reproject_feature(config['geom'], 'EPSG:3857')
    trsf_bounds = bounds(trsf_geom)
    dx = trsf_bounds[2] - trsf_bounds[0]
    dy = trsf_bounds[3] - trsf_bounds[1]
    area = abs(dx * dy)
    if area > const.MAX_AREA:
        raise PixelsFailed('Input geometry bounding box area of {:0.1f} km2 is too large (max 100 km2).'.format(const.MAX_AREA / 1e6))

    logger.info('Geometry area bbox is {:0.1f} km2.'.format(area / 1e6))

    # Override the original geometry if it was in 4326.
    if config['geom']['crs'] == 'EPSG:4326':
        config['geom'] = trsf_geom
        config['geom']['crs'] = 'EPSG:3857'

    # Get extract custom handler arguments.
    composite = config.pop('composite', False)
    latest_pixel = config.pop('latest_pixel', False)
    color = config.pop('color', False)
    bands = config.pop('bands', [])
    scale = config.pop('scale', 10)
    delay = config.pop('delay', False)
    tag = config.pop('tag', False)
    search_only = config.pop('search_only', False)
    clip_to_geom = config.pop('clip_to_geom', False)
    file_format = config.pop('format', const.REQUEST_FORMAT_ZIP).upper()
    max_cloud_cover_percentage = config.pop('max_cloud_cover_percentage', 100)

    # Sanity checks.
    if 'geom' not in config:
        raise PixelsFailed('Geom is required. Please specify "geom" key.')

    if 'start' not in config:
        raise PixelsFailed('Start date is required. Please specify "start" key.')
    else:
        try:
            start = parser.parse(config['start'])
        except:
            raise PixelsFailed('Start date not valid, please specify a valid start date string like "2016-08-01".')

    if 'end' not in config:
        raise PixelsFailed('End date is required. Please specify "end" key.')
    else:
        try:
            end = parser.parse(config['end'])
        except:
            raise PixelsFailed('End date not valid, please specify a valid end date string like "2016-08-01".')

    if end < start:
        # Ensure dates are valid and in right order.
        raise PixelsFailed('End date is later than start date.')

    if 'product_type' not in config:
        raise PixelsFailed('Product type is required. Please specify "product_type" key.')

    if file_format not in const.REQUEST_FORMATS:
        raise PixelsFailed('Request format {} not recognized. Use one of {}'.format(file_format, const.REQUEST_FORMATS))

    if not composite and not latest_pixel:
        raise PixelsFailed('Choose either latest pixel or composite mode.')

    if composite and config.get('platform', None) == const.PLATFORM_SENTINEL_1:
        raise PixelsFailed('Cannot compute composite for Sentinel 1.')

    if delay and search_only:
        raise PixelsFailed('Search only mode works in synchronous mode only.')

    if 'interval' in config and config['interval'] not in const.TIMESERIES_INTERVALS:
        raise PixelsFailed('Timeseries interval {} not recognized. Use one of {}'.format(config['interval'], const.TIMESERIES_INTERVALS))

    if 'interval' in config and search_only:
        raise PixelsFailed('Timeseries requests do not support search_only mode.')

    if 'interval_step' in config:
        try:
            config['interval_step'] = int(config['interval_step'])
        except ValueError:
            raise PixelsFailed('Interval step needs to be an integer.')

    # For composite, we will require all bands to be retrieved.
    if composite and not len(bands) == len(const.SENTINEL_2_BANDS):
        if config['product_type'] == const.PRODUCT_L2A:
            logger.info('Adding SCL for composite mode.')
            bands = list(set(bands + ['SCL']))
        else:
            logger.info('Adding all Sentinel-2 bands for composite mode.')
            bands = const.SENTINEL_2_BANDS

    # For color, assure the RGB bands are present.
    if file_format == const.REQUEST_FORMAT_PNG and config['platform'] == const.PLATFORM_SENTINEL_2:
        # For render, only request RGB bands.
        bands = const.SENTINEL_2_RGB_BANDS
    elif color and config['platform'] == const.PLATFORM_SENTINEL_2 and not all([dat in bands for dat in const.SENTINEL_2_RGB_BANDS]):
        logger.info('Adding RGB bands for color mode.')
        bands = list(set(bands + const.SENTINEL_2_RGB_BANDS))
    elif color and config['platform'] == const.PLATFORM_SENTINEL_1:
        # TODO: Allow other polarisation modes.
        bands = const.SENTINEL_1_POLARISATION_MODE['DV']
        bands = [band.lower() for band in bands]

    # Store possible config overrides.
    config['composite'] = composite
    config['latest_pixel'] = latest_pixel
    config['color'] = color
    config['bands'] = bands
    config['scale'] = scale
    config['format'] = file_format
    config['search_only'] = search_only
    config['clip_to_geom'] = clip_to_geom
    config['max_cloud_cover_percentage'] = max_cloud_cover_percentage
    config['delay'] = delay
    config['tag'] = tag

    logger.info('Configuration is {}'.format(config))

    return config
