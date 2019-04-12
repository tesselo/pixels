import copy
import json
import logging
import zipfile
from io import BytesIO

import numpy
from PIL import Image

from flask import Flask, jsonify, request, send_file
from pixels import const, scihub, search

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@app.route('/', methods=['GET', 'POST'])
def pixels(event=None, context=None):
    """
    AWS Lambda ready handler for the pixels package.

    The input event is a JSON configuration for a pixels request.
    """
    # Retrun message on GET.
    if request.method == 'GET':
        # Look for a json string in data argument.
        data = json.loads(request.args['data'])
    else:
        # Retrieve json data from post request.
        data = request.get_json()
    print(data)

    # Get extract custom handler arguments.
    search_only = data.pop('search_only', False)
    composite = data.pop('composite', False)
    latest_pixel = data.pop('latest_pixel', False)
    color = data.pop('color', False)
    bands = data.pop('bands', [])
    scale = data.pop('scale', 10)
    render = data.pop('render', False)

    if not composite and not latest_pixel:
        # TODO: Allow getting multiple stacks as "raw" scenes data.
        raise ValueError('Choose either latest pixel or composite mode.')

    # Sanity checks.
    if composite and data.get('platform', None) == const.PLATFORM_SENTINEL_1:
        raise ValueError('Cannot compute composite for Sentinel 1.')

    # For composite, we will require all bands to be retrieved.
    if composite and not len(bands) == len(const.SENTINEL_2_BANDS):
        if data['product_type'] == const.PRODUCT_L2A:
            logger.info('Adding SCL for composite mode.')
            bands = list(set(bands + ['SCL']))
        else:
            logger.info('Adding all Sentinel-2 bands for composite mode.')
            bands = const.SENTINEL_2_BANDS
    # For color, assure the RGB bands are present.
    if color and data['platform'] == const.PLATFORM_SENTINEL_2 and not all([dat in bands for dat in const.SENTINEL_2_RGB_BANDS]):
        logger.info('Adding RGB bands for color mode.')
        bands = list(set(bands + const.SENTINEL_2_RGB_BANDS))
    elif color and data['platform'] == const.PLATFORM_SENTINEL_1:
        # TODO: Allow other polarisation modes.
        bands = const.SENTINEL_1_POLARISATION_MODE['DV']
        bands = [band.lower() for band in bands]

    # Store original data and possible overrides.
    config_log = copy.deepcopy(data)
    config_log['search_only'] = search_only
    config_log['composite'] = composite
    config_log['latest_pixel'] = latest_pixel
    config_log['color'] = color
    config_log['bands'] = bands
    config_log['scale'] = scale
    logger.info('Configuration is {}'.format(config_log))

    # Query available scenery.
    logger.info('Querying data on the ESA SciHub.')
    query_result = search.search(**data)

    # Return only search query if requested.
    if search_only:
        return jsonify(query_result)

    # Get pixels.
    if latest_pixel:
        logger.info('Getting latest pixels stack.')
        stack = scihub.latest_pixel(data['geom'], query_result, scale=scale, bands=bands, as_file=True)
    else:
        for entry in query_result:
            logger.info('Getting scene pixels for {}.'.format(entry['prefix']))
            entry['pixels'] = scihub.get_pixels(data['geom'], entry, scale=scale, bands=bands)

        if composite:
            logger.info('Computing composite from pixel stacks.')
            stack = [entry['pixels'] for entry in query_result]
            stack = scihub.s2_composite(stack, as_file=True)

    # Convert to RGB color tif.
    if color:
        logger.info('Computing RGB image from stack.')
        if data.get('platform', None) == const.PLATFORM_SENTINEL_1:
            stack['RGB'] = scihub.s1_color(stack, as_file=True)
        else:
            stack['RGB'] = scihub.s2_color(stack, as_file=True)

        if render:
            pixpix = numpy.array([
                numpy.clip(stack['RGB'].open().read(1), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                numpy.clip(stack['RGB'].open().read(2), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                numpy.clip(stack['RGB'].open().read(3), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
            ]).astype('uint8')

            img = Image.fromarray(pixpix.T)

            # Save image to io buffer.
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            return send_file(
                output,
                mimetype='image/png'
            )

    # Write all result rasters into a zip file and return the data package.
    logger.info('Packaging data into zip file.')
    bytes_buffer = BytesIO()
    with zipfile.ZipFile(bytes_buffer, 'w') as zf:
        # Write pixels into zip file.
        for key, raster in stack.items():
            raster.seek(0)
            zf.writestr('{}.tif'.format(key), raster.read())
        # Write config into zip file.
        zf.writestr('config.json', json.dumps(config_log))

    # Rewind buffer.
    bytes_buffer.seek(0)

    # Return buffer as file.
    return send_file(
        bytes_buffer,
        as_attachment=True,
        attachment_filename='pixels.zip',
        mimetype='application/zip'
    )
