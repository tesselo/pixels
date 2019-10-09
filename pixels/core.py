import json
import logging
import zipfile
from collections import OrderedDict
from io import BytesIO

import numpy
from PIL import Image, ImageEnhance
from rasterio import Affine

from pixels import const, scihub, search, utils

# Get logger.
logger = logging.getLogger(__name__)


def handler(config):
    """
    AWS Lambda ready handler for the pixels package.

    The input event is a JSON configuration for a pixels request.
    """
    # Query available scenery.
    logger.info('Querying data on the ESA SciHub.')
    query_result = search.search(
        geom=config['geom'],
        start=config['start'],
        end=config['end'],
        platform=config['platform'],
        product_type=config['product_type'],
        s1_acquisition_mode=config.get('s1_acquisition_mode', None),
        s1_polarisation_mode=config.get('s1_polarisation_mode', None),
        max_cloud_cover_percentage=config['max_cloud_cover_percentage'],
        sort_by_cloud_cover=config.get('sort_by_cloud_cover', True),
    )

    if not len(query_result):
        return

    # Return only search query if requested.
    if config['mode'] == const.MODE_SEARCH_ONLY:
        return query_result

    # Compute affine transform from input.
    if 'target_geotransform' in config:
        trf = config['target_geotransform']
        transform = Affine(trf['scale_x'], trf['skew_x'], trf['origin_x'], trf['skew_y'], trf['scale_y'], trf['origin_y'])
        width = trf['width']
        height = trf['height']
        crs = config['geom']['crs']
    else:
        transform, width, height, crs = utils.compute_transform(config['geom'], config['scale'])

    # Get pixels.
    if config['mode'] == const.MODE_LATEST_PIXEL:
        logger.info('Getting latest pixels stack with {} entries.'.format(len(query_result)))
        stack = scihub.latest_pixel(transform, width, height, crs, query_result, bands=config['bands'])
    elif config['mode'] == const.MODE_COMPOSITE:
        logger.info('Computing composite from pixel stacks with {} entries.'.format(len(query_result)))
        stack = scihub.s2_composite(transform, width, height, crs, query_result, config['bands'])
    elif config['mode'] == const.MODE_COMPOSITE_INCREMENTAL:
        logger.info('Computing incremental composite from pixel stacks with {} entries.'.format(len(query_result)))
        stack = scihub.s2_composite_incremental(transform, width, height, crs, query_result, config['bands'])
    elif config['mode'] == const.MODE_COMPOSITE_NN:
        logger.info('Computing Neural Network based composite from pixel stacks with {} entries.'.format(len(query_result)))
        stack = scihub.s2_composite_nn(transform, width, height, crs, query_result, config['bands'], config['product_type'])
    elif config['mode'] == const.MODE_COMPOSITE_INCREMENTAL_NN:
        logger.info('Computing Neural Network based incremental composite from pixel stacks with {} entries.'.format(len(query_result)))
        stack = scihub.s2_composite_incremental_nn(transform, width, height, crs, query_result, config['bands'], config['product_type'])

    # Clip to geometry if requested.
    if config['clip_to_geom']:
        stack = utils.clip_to_geom(stack, config['geom'], config.get('clip_all_touched', True))

    # Add formulas if requested.
    if 'formulas' in config:
        stack = utils.algebra(stack, config['formulas'])

    # Convert to RGB color tif.
    if config['color']:
        logger.info('Computing RGB image from stack.')
        if config.get('platform', None) == const.PLATFORM_SENTINEL_1:
            stack['RGB'] = scihub.s1_color(stack)
        else:
            stack['RGB'] = scihub.s2_color(stack)

    # Render data into requested format.
    output = BytesIO()

    if config['format'] == const.REQUEST_FORMAT_PNG:
        logger.info('Rendering RGB data into PNG image.')
        pixpix = numpy.array([
            numpy.clip(stack['RGB'].open().read(1), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
            numpy.clip(stack['RGB'].open().read(2), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
            numpy.clip(stack['RGB'].open().read(3), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
        ]).astype('uint8')

        # Create image object
        img = Image.fromarray(pixpix.T)
        # Enhance color scheme for Sentinel-2 true color rendering.
        if config.get('platform', None) == const.PLATFORM_SENTINEL_2:
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Brightness(img).enhance(1.8)
            img = ImageEnhance.Color(img).enhance(1.4)

        # Save image to io buffer.
        img.save(output, format=const.REQUEST_FORMAT_PNG)
    elif config['format'] == const.REQUEST_FORMAT_ZIP:
        logger.info('Packaging data into zip file.')
        with zipfile.ZipFile(output, 'w') as zf:
            # Write pixels into zip file.
            for key, raster in stack.items():
                raster.seek(0)
                zf.writestr('{}.tif'.format(key), raster.read())
            # Write config into zip file.
            zf.writestr('config.json', json.dumps(config))
    elif config['format'] == const.REQUEST_FORMAT_NPZ:
        logger.info('Packaging data into numpy npz file.')
        # Convert stack to numpy arrays.
        stack = {key: val.open().read(1) for key, val in stack.items()}
        # Save to compressed numpy npz format.
        numpy.savez_compressed(
            output,
            config=config,
            **stack
        )
    elif config['format'] == const.REQUEST_FORMAT_CSV:
        logger.info('Packaging data into a csv file.')
        # Extract raster profile to compute pixel coordinates.
        with next(iter(stack.values())).open() as rst:
            profile = rst.profile
        width = profile['width']
        height = profile['height']
        scale_x = profile['transform'][0]
        origin_x = profile['transform'][2]
        scale_y = profile['transform'][4]
        origin_y = profile['transform'][5]

        # Compute point coordinates for all pixels.
        coords_x = numpy.array([origin_x + scale_x * idx for idx in range(width)] * height)
        coords_y = numpy.tile([origin_y + scale_y * idx for idx in range(height)], (width, 1)).T.ravel()

        # Reproject pixel coords to original coordinate system if required.
        if 'properties' in config['geom'] and 'original_crs' in config['geom']['properties']:
            coords = utils.reproject_coords(
                [list(zip(coords_x, coords_y))],
                config['geom']['crs'],
                config['geom']['properties']['original_crs']
            )
            coords_x = numpy.array([dat[0] for dat in coords[0]])
            coords_y = numpy.array([dat[1] for dat in coords[0]])

        # List geom properties as columns.
        attrs = OrderedDict({key: numpy.array([val] * len(coords_x)) for key, val in config['geom']['properties'].items() if key != 'original_crs'})

        # Get pixel values by band in an ordered dict.
        stack = OrderedDict({key: val.open().read(1).ravel() for key, val in stack.items() if key != 'RGB'})

        # Construct csv header.
        if attrs:
            header = 'x,y,{},{}'.format(
                ','.join(attrs.keys()),
                ','.join(stack.keys()),
            )
        else:
            header = 'x,y,{}'.format(','.join(stack.keys()))

        # Construct csv data frame.
        data = numpy.rec.fromarrays([coords_x, coords_y] + list(attrs.values()) + list(stack.values())).T
        fmt = ['%.18e'] * 2 + ['%s'] * len(attrs) + ['%.18e'] * len(stack)
        # Save to memfile.
        numpy.savetxt(output, data, delimiter=',', header=header, comments='', fmt=fmt)

    # Rewind buffer.
    output.seek(0)

    return output
