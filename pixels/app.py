import copy
import json
import zipfile
from io import BytesIO
import logging

from pixels import const, scihub, search
from flask import Flask, send_file, request, jsonify

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@app.route('/', methods=['GET', 'POST'])
def pixels(event=None, context=None):
    """
    AWS Lambda ready handler for the pixels package.

    The input event is a JSON configuration for a pixels request.
    """
    print('event', event)
    print('context', context)

    if request.method == 'GET':
        return "Use POST to query pixels!", 200

    data = request.get_json()
    print('data', data)

    # Get extract custom handler arguments.
    search_only = data.pop('search_only', False)
    composite = data.pop('composite', False)
    latest_pixel = data.pop('latest_pixel', False)
    color = data.pop('color', False)
    bands = data.pop('bands', [])
    scale = data.pop('scale', 10)

    if not composite and not latest_pixel:
        # TODO: Allow getting multiple stacks as "raw" scenes data.
        raise ValueError('Choose either latest pixel or composite mode.')

    # Sanity checks.
    if composite and data.get('platform', None) == const.PLATFORM_SENTINEL_1:
        raise ValueError('Cannot compute composite for Sentinel 1.')

    # For composite, we will require all bands to be retrieved.
    if composite and not len(bands) == len(const.SENTINEL_2_BANDS):
        print('Requesting all Sentinel-2 bands for composite mode.')
        bands = const.SENTINEL_2_BANDS

    # Store original data and possible overrides.
    config_log = copy.deepcopy(data)
    config_log['search_only'] = search_only
    config_log['composite'] = composite
    config_log['latest_pixel'] = latest_pixel
    config_log['color'] = color
    config_log['bands'] = bands
    config_log['scale'] = scale

    # Query available scenery.
    print('Querying data on the ESA SciHub.', data)
    query_result = search.search(**data)

    # Return only search query if requested.
    if search_only:
        return jsonify(query_result)

    # Get pixels.
    if latest_pixel:
        print('Getting latest pixels stack.')
        stack = scihub.latest_pixel(data['geom'], query_result, scale=scale, bands=bands, as_file=True)
    else:
        #### HACK TODO REMOVE
        #BD2 = scihub.get_pixels(data['geom'], query_result[0], scale=scale, bands=['B02'])['B02']

        for entry in query_result:
            print('Getting scene pixels for', entry['prefix'])
            entry['pixels'] = scihub.get_pixels(data['geom'], entry, scale=scale, bands=bands)
            #entry['pixels'] = {key: BD2 for key in const.SENTINEL_2_BANDS}

        if composite:
            print('Computing composite from pixel stacks.')
            stack = [entry['pixels'] for entry in query_result]
            stack = scihub.s2_composite(stack, as_file=True)

    # Convert to RGB color tif.
    if color:
        print('Computing RGB image from stack.')
        if data.get('platform', None) == const.PLATFORM_SENTINEL_1:
            stack['RGB'] = scihub.s1_color(stack, as_file=True)
        else:
            stack['RGB'] = scihub.s2_color(stack, as_file=True)

    # Write all result rasters into a zip file and return the data package.
    print('Packaging data into zip file.')
    bytes_buffer = BytesIO()
    with zipfile.ZipFile(bytes_buffer, 'w') as zf:
        # Write pixels into zip file.
        for key, raster in stack.items():
            raster.seek(0)
            zf.writestr('{}.tif'.format(key), raster.read())
        # Write config into zip file.
        zf.writestr('config.json', json.dumps(config_log))

    bytes_buffer.seek(0)
    return send_file(
        bytes_buffer,
        as_attachment=True,
        attachment_filename='pixels.zip',
        mimetype='application/zip'
    )
