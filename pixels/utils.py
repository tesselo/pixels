import logging
import math
import uuid
from copy import deepcopy

import numpy
import rasterio
from dateutil import parser
from dateutil.relativedelta import relativedelta
from pyproj import Proj, transform
from rasterio import Affine
from rasterio.features import bounds, rasterize
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject
from shapely.geometry import Polygon, shape

from pixels import const
from pixels.algebra import FormulaParser
from pixels.exceptions import PixelsFailed

# Get logger.
logger = logging.getLogger(__name__)


def generate_unique_key(frmt, ts_tag='', ts_tag_is_main_key=False):
    """
    Generate a unique S3 file key to upload files to.
    """
    if ts_tag:
        ts_tag = '{}/'.format(ts_tag)

    tag = '' if ts_tag_is_main_key else '{}/'.format(uuid.uuid4())

    return '{}{}pixels.{}'.format(
        ts_tag,
        tag,
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
    width = math.ceil((extent[2] - extent[0]) / scale)
    height = math.ceil((extent[3] - extent[1]) / scale)

    return transform, width, height, geom['crs']


def tile_scale(z):
    """
    Calculate tile pixel size scale for given zoom level.
    """
    TILESIZE = 256
    WEB_MERCATOR_WORLDSIZE = 2 * math.pi * 6378137
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
            'resampling': Resampling.nearest if 'SCL.jp2' in prefix else Resampling.cubic,
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
    # Get creation args from parent raster.
    creation_args = rst.meta.copy()
    # Ensure correct data type.
    creation_args['dtype'] = data.dtype
    # Create target raster and write band data to it.
    memfile = MemoryFile()
    with memfile.open(**creation_args) as dst:
        dst.write(data.reshape((1, ) + (rst.height, rst.width)))
    # Return memfile object.
    return memfile


def tile_bounds(z, x, y):
    """
    Calculate the bounding box of a specific tile.
    """
    WEB_MERCATOR_WORLDSIZE = 2 * math.pi * 6378137

    WEB_MERCATOR_TILESHIFT = WEB_MERCATOR_WORLDSIZE / 2.0

    zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

    xmin = x * zscale - WEB_MERCATOR_TILESHIFT
    xmax = (x + 1) * zscale - WEB_MERCATOR_TILESHIFT
    ymin = WEB_MERCATOR_TILESHIFT - (y + 1) * zscale
    ymax = WEB_MERCATOR_TILESHIFT - y * zscale

    return [xmin, ymin, xmax, ymax]


def tile_index(lng, lat, zoom):
    """
    Calcluate tile index from lat/lon for a given zoom level.
    """
    lat = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int(math.floor((lng + 180.0) / 360.0 * n))

    try:
        ytile = int(math.floor((1.0 - math.log(
            math.tan(lat) + (1.0 / math.cos(lat))) / math.pi) / 2.0 * n))
    except ValueError:
        raise ValueError("Y can not be computed for latitude {} radians".format(lat))
    else:
        return xtile, ytile, zoom


def tile_range(geom, zoom, intersection=False, tolerance=0):
    """
    Compute tile range of TMS tiles intersecting with the input geometry at the
    given zoom level.
    """
    # Compute general tile bounds.
    geombounds = rasterio.features.bounds(reproject_feature(geom, 'EPSG:4326'))
    minimumTile = tile_index(geombounds[0], geombounds[3], zoom)
    maximumTile = tile_index(geombounds[2], geombounds[1], zoom)
    logger.info('Tile range is {} - {}'.format(minimumTile, maximumTile))

    # Convert geometry to shape.
    geom_shape = shape(reproject_feature(geom, 'EPSG:3857')['geometry'])

    # Loop through all tiles but only yeald the intersecting ones.
    for x in range(minimumTile[0], maximumTile[0] + 1):
        for y in range(minimumTile[1], maximumTile[1] + 1):

            # Compute tile bounds.
            tbounds = tile_bounds(zoom, x, y)

            if tolerance:
                tbounds[0] += tolerance
                tbounds[2] += tolerance
                tbounds[1] -= tolerance
                tbounds[3] -= tolerance

            # Instanciate tile polygon.
            tile = Polygon([
                [tbounds[0], tbounds[1]],
                [tbounds[2], tbounds[1]],
                [tbounds[2], tbounds[3]],
                [tbounds[0], tbounds[3]],
                [tbounds[0], tbounds[1]],
            ])

            # Yield tile index if the tile intersects with the geometry. Also
            # include tile intersection geometry if requested.
            if intersection:
                tile_intersection = tile.intersection(geom_shape)
                if tile_intersection:
                    yield x, y, tile_intersection
            elif tile.intersects(geom_shape):
                yield x, y


def clip_to_geom(stack, geom, all_touched=True):
    """
    Clip all rasters in this stack to the geometry.
    """
    # Compute mask from geom.
    with next(iter(stack.values())).open() as rst:
        mask = rasterize([geom['geometry']], out_shape=rst.shape, transform=rst.transform, all_touched=all_touched).astype('bool')
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


def reproject_coords(coords, src, tar):
    """
    Reproject a list of polygon coordinates.
    """
    if len(coords) > 1:
        raise ValueError('Polygons with interior rings are not supported.')

    if isinstance(src, str):
        src = Proj(init=src)
    if isinstance(tar, str):
        tar = Proj(init=tar)

    transformed_coords = []
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


def timeseries_steps(start, end, interval, interval_step):
    """
    Construct a series of timesteps given the input date range.
    """
    # Convert input to dates if provided as str.
    if isinstance(start, str):
        start = parser.parse(start)
    if isinstance(end, str):
        end = parser.parse(end)
    # Compute time delta.
    delta = relativedelta(**{interval.lower(): int(interval_step)})
    one_day = relativedelta(days=1)
    # Create intermediate timestamps.
    here_start = start
    here_end = start + delta
    # Loop through timesteps.
    while (here_end - one_day) <= end:
        yield here_start, here_end - one_day
        # Increment intermediate timestamps.
        here_start += delta
        here_end += delta


def algebra(stack, formulas):
    """
    Evaluate raster algebra formula on this stack.
    """
    parser = FormulaParser()
    data = {key: rst.open().read().ravel() for key, rst in stack.items()}
    for formula in formulas:
        result = parser.evaluate(data, formula['expression'])
        with next(iter(stack.values())).open() as rst:
            stack[formula['name']] = clone_raster(rst, result)
    return stack


def choose(selector, choices):
    """
    A simplified version of the numpy choose function to workaround the 32
    choices limit.
    """
    if isinstance(choices[0], (int, float)):
        return numpy.array([choices[selector[idx]] for idx in numpy.lib.index_tricks.ndindex(selector.shape)]).reshape(selector.shape)
    else:
        return numpy.array([choices[selector[idx]][idx] for idx in numpy.lib.index_tricks.ndindex(selector.shape)]).reshape(selector.shape)


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
        raise PixelsFailed('Input geometry bounding box area of {:0.1f} km2 is too large (max {:0.1f} km2).'.format(area / 1e6, const.MAX_AREA / 1e6))

    logger.info('Geometry area bbox is {:0.1f} km2.'.format(area / 1e6))

    # Override the original geometry if it was in 4326.
    if config['geom']['crs'] == 'EPSG:4326':
        config['geom'] = trsf_geom
        config['geom']['crs'] = 'EPSG:3857'
        # Track the original crs for reference.
        if 'properties' not in config['geom']:
            config['geom']['properties'] = {}
        config['geom']['properties']['original_crs'] = 'EPSG:4326'

    # Get extract custom handler arguments.
    mode = config.pop('mode', False)
    color = config.pop('color', False)
    bands = config.pop('bands', [])
    scale = config.pop('scale', 10)
    delay = config.pop('delay', False)
    tag = config.pop('tag', False)
    clip_to_geom = config.pop('clip_to_geom', False)
    file_format = config.pop('format', const.REQUEST_FORMAT_ZIP).upper()
    max_cloud_cover_percentage = config.pop('max_cloud_cover_percentage', 100)

    # Sanity checks.
    if 'platform' not in config:
        raise PixelsFailed('Platform name is required. Please specify "platform" key.')

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

    if mode not in const.MODES:
        raise PixelsFailed('Mode {} not recognized. Use one of {}.'.format(mode, const.MODES))

    if mode in (const.MODE_COMPOSITE, const.MODE_COMPOSITE_INCREMENTAL, const.MODE_COMPOSITE_NN, const.MODE_COMPOSITE_INCREMENTAL_NN):
        if config.get('platform') == const.PLATFORM_SENTINEL_1:
            raise PixelsFailed('Cannot compute composite for Sentinel 1.')

    if delay and mode == const.MODE_SEARCH_ONLY:
        raise PixelsFailed('Search only mode works in synchronous mode only.')

    if 'interval' in config and config['interval'] not in const.TIMESERIES_INTERVALS:
        raise PixelsFailed('Timeseries interval {} not recognized. Use one of {}'.format(config['interval'], const.TIMESERIES_INTERVALS))

    if 'interval' in config and mode == const.MODE_SEARCH_ONLY:
        raise PixelsFailed('Timeseries requests do not support search_only mode.')

    if 'interval_step' in config:
        try:
            config['interval_step'] = int(config['interval_step'])
        except ValueError:
            raise PixelsFailed('Interval step needs to be an integer.')

    # Formulas.
    for formula in config.get('formulas', []):
        if not isinstance(formula, dict):
            raise PixelsFailed('Formulas key must be a list of formula dictionaries.')
        if 'name' not in formula:
            raise PixelsFailed('Each formlua requires a name.')
        if 'expression' not in formula:
            raise PixelsFailed('Each formula requires an expression.')

    # Geotransform.
    if 'target_geotransform' in config:
        if not isinstance(config['target_geotransform'], dict):
            raise PixelsFailed('Target geotransform should be a dictionary.')
        if not config['target_geotransform'].keys() == {"width": 1, "height": 1, "origin_x": 0, "scale_x": 1, "skew_x": 0, "origin_y": 0, "skew_y": 0, "scale_y": -1}.keys():
            raise PixelsFailed('Target geotransform invalid.')

    # Sentinel-1
    if config.get('platform') == const.PLATFORM_SENTINEL_1:
        if 's1_acquisition_mode' not in config:
            raise ValueError('Sentinel-1 "s1_acquisition_mode" parameter is required')
        elif config.get('s1_acquisition_mode') not in [const.MODE_SM, const.MODE_IW, const.MODE_EW, const.MODE_WV]:
            raise ValueError('Unknown acquisition mode "{}" for Sentinel-1'.format(config.get('s1_acquisition_mode')))

        if config.get('product_type') not in [const.PRODUCT_GRD, const.PRODUCT_SLC, const.PRODUCT_OCN]:
            raise ValueError('Unknown product type "{}" for Sentinel-1'.format(config.get('product_type')))

    # Override color flag if PNG is requested, as in that case RGB bands are
    # required.
    if file_format == const.REQUEST_FORMAT_PNG:
        color = True

    # Band 10 is not available for L2A.
    if config['product_type'] == const.PRODUCT_L2A and 'B10' in bands:
        logger.info('Band B10 is not available for L2A mode, removing it from list.')
        bands = [band for band in bands if band != 'B10']

    # Band SCL is not available for L1C.
    if config['product_type'] == const.PRODUCT_L1C and 'SCL' in bands:
        logger.info('Band SCL is not available for L2A mode, removing it from list.')
        bands = [band for band in bands if band != 'SCL']

    # For composite, we will require all bands to be retrieved.
    if mode == const.MODE_COMPOSITE:
        if config['product_type'] == const.PRODUCT_L2A:
            logger.info('Adding SCL and NDVI bands for composite mode.')
            bands = list(set(bands + ['SCL', 'B04', 'B08']))
        elif len(bands) != len(const.SENTINEL_2_BANDS):
            logger.info('Adding NDVI bands for composite mode.')
            bands = list(set(bands + ['B04', 'B08']))
    elif mode == const.MODE_COMPOSITE_INCREMENTAL:
        if config['product_type'] != const.PRODUCT_L2A:
            raise PixelsFailed('Composite incremental mode is only available for L2A.')
        logger.info('Adding SCL band for composite incremental mode.')
        bands = list(set(bands + ['SCL']))
    elif mode in (const.MODE_COMPOSITE_NN, const.MODE_COMPOSITE_INCREMENTAL_NN):
        logger.info('Adding all bands for composite mode.')
        if config['product_type'] == const.PRODUCT_L2A:
            bands = list(set(bands + ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B11', 'B12']))
        elif len(bands) != len(const.SENTINEL_2_BANDS):
            bands = const.SENTINEL_2_BANDS

    # For color, assure the RGB bands are present.
    if file_format == const.REQUEST_FORMAT_PNG and config['platform'] == const.PLATFORM_SENTINEL_2:
        # For render, only request RGB bands.
        bands = list(set(bands + const.SENTINEL_2_RGB_BANDS))
    elif color and config['platform'] == const.PLATFORM_SENTINEL_2 and not all([dat in bands for dat in const.SENTINEL_2_RGB_BANDS]):
        logger.info('Adding RGB bands for color mode.')
        bands = list(set(bands + const.SENTINEL_2_RGB_BANDS))
    elif color and config['platform'] == const.PLATFORM_SENTINEL_1:
        # TODO: Allow other polarisation modes.
        bands = const.SENTINEL_1_POLARISATION_MODE['DV']
        bands = [band.lower() for band in bands]

    # Store possible config overrides.
    config['mode'] = mode
    config['color'] = color
    config['bands'] = bands
    config['scale'] = scale
    config['format'] = file_format
    config['clip_to_geom'] = clip_to_geom
    config['max_cloud_cover_percentage'] = max_cloud_cover_percentage
    config['delay'] = delay
    config['tag'] = tag

    logger.info('Configuration is {}'.format(config))

    return config
