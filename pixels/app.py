import copy
import json
import zipfile
from io import BytesIO

from pixels import const, scihub, search
from flask import Flask, send_file, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def handler():
    """
    AWS Lambda ready handler for the pixels package.

    The input event is a JSON configuration for a pixels request.
    """
    if request.method == 'GET':
        return "Use POST to query pixels!", 200

    event = request.get_json()
    # Get extract custom handler arguments.
    search_only = event.pop('search_only', False)
    composite = event.pop('composite', False)
    latest_pixel = event.pop('latest_pixel', False)
    color = event.pop('color', False)
    bands = event.pop('bands', [])
    scale = event.pop('scale', 10)

    if not composite and not latest_pixel:
        # TODO: Allow getting multiple stacks as "raw" scenes data.
        raise ValueError('Choose either latest pixel or composite mode.')

    # Sanity checks.
    if composite and event.get('platform', None) == const.PLATFORM_SENTINEL_1:
        raise ValueError('Cannot compute composite for Sentinel 1.')

    # For composite, we will require all bands to be retrieved.
    if composite and not len(bands) == len(const.SENTINEL_2_BANDS):
        print('Requesting all Sentinel-2 bands for composite mode.')
        bands = const.SENTINEL_2_BANDS

    # Store original event and possible overrides.
    config_log = copy.deepcopy(event)
    config_log['search_only'] = search_only
    config_log['composite'] = composite
    config_log['latest_pixel'] = latest_pixel
    config_log['color'] = color
    config_log['bands'] = bands
    config_log['scale'] = scale

    # Query available scenery.
    print('Querying data on the ESA SciHub.', event)
    query_result = search.search(**event)

    # Return only search query if requested.
    if search_only:
        return query_result

    # Get pixels.
    if latest_pixel:
        print('Getting latest pixels stack.')
        stack = scihub.latest_pixel(event['geom'], query_result, scale=scale, bands=bands, as_file=True)
    else:
        #### HACK TODO REMOVE
        #BD2 = scihub.get_pixels(event['geom'], query_result[0], scale=scale, bands=['B02'])['B02']

        for entry in query_result:
            print('Getting scene pixels for', entry['prefix'])
            entry['pixels'] = scihub.get_pixels(event['geom'], entry, scale=scale, bands=bands)
            #entry['pixels'] = {key: BD2 for key in const.SENTINEL_2_BANDS}

        if composite:
            print('Computing composite from pixel stacks.')
            stack = [entry['pixels'] for entry in query_result]
            stack = scihub.s2_composite(stack, as_file=True)

    # Convert to RGB color tif.
    if color:
        print('Computing RGB image from stack.')
        if event.get('platform', None) == const.PLATFORM_SENTINEL_1:
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

    return send_file(bytes_buffer)
