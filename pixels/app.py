import datetime
import functools
import json
import logging
import uuid
import zipfile
from io import BytesIO

import boto3
import numpy
from dateutil import parser
from flask import Flask, Response, has_request_context, jsonify, redirect, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageEnhance
from zappa.async import task

from pixels import const, scihub, search, utils, wmts
from pixels.exceptions import PixelsFailed

# Flask setup
app = Flask(__name__)
app.config.from_pyfile('config.py')

# Logging setup
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DB Setup
db = SQLAlchemy(app)


class RasterApiReadonlytoken(db.Model):
    key = db.Column(db.String(40), primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    created = db.Column(db.DateTime)

    def __repr__(self):
        return 'Token %r' % self.key


def token_required(func):
    """
    Decorator to check for auth token.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Only run the test if the function is called as a view.
        if has_request_context():
            key = request.args.get('key', None)
            if not key:
                raise PixelsFailed('Authentication key is required.')
            token = RasterApiReadonlytoken.query.get(key)
            if not token:
                raise PixelsFailed('Authentication key is not valid.')
        return func(*args, **kwargs)

    return wrapper


@app.errorhandler(PixelsFailed)
def handle_pixels_error(exc):
    response = jsonify(exc.to_dict())
    response.status_code = exc.status_code
    return response


@app.route('/', methods=['GET'])
@token_required
def index():
    return render_template('index.html')


@app.route('/docs', methods=['GET'])
@token_required
def docs():
    return render_template('docs.html')


@app.route('/data', methods=['GET', 'POST'])
@token_required
def pixels(data=None):
    """
    AWS Lambda ready handler for the pixels package.

    The input event is a JSON configuration for a pixels request.
    """
    if not data:
        # Retrun message on GET.
        if request.method == 'GET':
            # Look for a json string in data argument.
            data = json.loads(request.args['data'])
        else:
            # Retrieve json data from post request.
            data = request.get_json()

    config = utils.validate_configuration(data)

    # Handle delay mode.
    if config['delay'] and not config['tag']:
        logger.info('Working in delay mode.')
        key = '{}/pixels.{}'.format(
            uuid.uuid4(),
            config['format'].lower(),
        )
        config['tag'] = key
        pixels_task(config)
        url = '{}async/{}?key={}'.format(request.host_url, key, request.args['key'])
        return jsonify(message='Getting pixels asynchronously. Your files will be ready at the link below soon.', url=url)

    # Query available scenery.
    logger.info('Querying data on the ESA SciHub.')
    query_result = search.search(
        geom=config['geom'],
        start=config['start'],
        end=config['end'],
        platform=config['platform'],
        product_type=config['product_type'],
        s1_acquisition_mode=None,
        s1_polarisation_mode=None,
        s2_max_cloud_cover_percentage=config['max_cloud_cover_percentage'],
    )

    # Return only search query if requested.
    if config['search_only']:
        return jsonify(query_result)

    if not len(query_result):
        raise PixelsFailed('No scenes found for the given search criteria.')

    # Get pixels.
    if config['latest_pixel']:
        logger.info('Getting latest pixels stack.')
        stack = scihub.latest_pixel(config['geom'], query_result, scale=config['scale'], bands=config['bands'])
    else:
        for entry in query_result:
            logger.info('Getting scene pixels for {}.'.format(entry['prefix']))
            entry['pixels'] = scihub.get_pixels(config['geom'], entry, scale=config['scale'], bands=config['bands'])

        if config['composite']:
            logger.info('Computing composite from pixel stacks.')
            stack = [entry['pixels'] for entry in query_result]
            stack = scihub.s2_composite(stack)

    # Clip to geometry if requested:
    if config['clip_to_geom']:
        stack = utils.clip_to_geom(stack, config['geom'])

    # Convert to RGB color tif.
    if config['color']:
        logger.info('Computing RGB image from stack.')
        if config.get('platform', None) == const.PLATFORM_SENTINEL_1:
            stack['RGB'] = scihub.s1_color(stack)
        else:
            stack['RGB'] = scihub.s2_color(stack)

        # Check for RGB render mode.
        if config['format'] == const.REQUEST_FORMAT_PNG:
            logger.info('Rendering RGB data into PNG image.')
            pixpix = numpy.array([
                numpy.clip(stack['RGB'].open().read(1), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                numpy.clip(stack['RGB'].open().read(2), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                numpy.clip(stack['RGB'].open().read(3), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
            ]).astype('uint8')

            # Create image object and enhance color scheme.
            img = Image.fromarray(pixpix.T)
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Brightness(img).enhance(1.8)
            img = ImageEnhance.Color(img).enhance(1.4)

            # Save image to io buffer.
            output = BytesIO()
            img.save(output, format=const.REQUEST_FORMAT_PNG)
            output.seek(0)
            if config['tag']:
                s3 = boto3.client('s3')
                s3.put_object(
                    Bucket=const.BUCKET,
                    Key=config['tag'],
                    Body=output,
                )
                return
            else:
                return send_file(
                    output,
                    mimetype='image/png'
                )

    # Write all result rasters into a zip file and return the data package.
    bytes_buffer = BytesIO()
    if config['format'] == const.REQUEST_FORMAT_ZIP:
        logger.info('Packaging data into zip file.')
        with zipfile.ZipFile(bytes_buffer, 'w') as zf:
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
            bytes_buffer,
            config=config,
            **stack
        )

    # Rewind buffer.
    bytes_buffer.seek(0)

    # Return buffer as file.
    if config['tag']:
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=const.BUCKET,
            Key=config['tag'],
            Body=bytes_buffer,
        )
    else:
        return send_file(
            bytes_buffer,
            as_attachment=True,
            attachment_filename='pixels.{}'.format(config['format'].lower()),
            mimetype='application/{}'.format(config['format'].lower())
        )


@task
def pixels_task(data):
    # Store tag for usage error in case the pixels call fails.
    tag = data['tag']
    try:
        pixels(data)
    except:
        s3 = boto3.client('s3')
        base = tag.split('/')[0]
        s3.put_object(
            Bucket=const.BUCKET,
            Key='{}/failed.txt'.format(base),
            Body=BytesIO(),
        )
        raise


@app.route('/async/<tag>/<file>', methods=['GET'])
@token_required
def asyncresult(tag, file):
    s3 = boto3.resource('s3')
    obj = s3.Object(const.BUCKET, '{}/{}'.format(tag, file))
    logger.info('Looking for result object {}/{} from async call.'.format(tag, file))
    try:
        obj = obj.get()
        logger.info('Found result object from async call.')
        url = boto3.client('s3').generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': const.BUCKET,
                'Key': '{}/{}'.format(tag, file),
            }
        )
        return redirect(url)
    except s3.meta.client.exceptions.NoSuchKey:
        try:
            s3.Object(const.BUCKET, '{}/failed.txt'.format(tag)).get()
        except s3.meta.client.exceptions.NoSuchKey:
            return jsonify('Async collection not finished yet.')
        else:
            return jsonify('Async collection falied.')


@app.route('/tiles/<int:z>/<int:x>/<int:y>.png', methods=['GET'])
@token_required
def tiles(z, x, y):
    """
    TMS tiles endpoint.
    """
    if z < 12:
        return utils.get_empty_tile()

    # Retrieve end date from query args.
    end = request.args.get('end')
    if not end:
        end = str(datetime.datetime.now().date())
    # Retrieve start date from query arg, default to 4 weeks before end.
    start = request.args.get('start')
    if not start:
        start = str((parser.parse(end) - datetime.timedelta(weeks=4)).date())
    # Get cloud cover filter.
    max_cloud_cover_percentage = int(request.args.get('max_cloud_cover_percentage', 20))
    # Compute tile bounds and scale.
    bounds = utils.tile_bounds(z, x, y)
    scale = utils.tile_scale(z)
    # Prepare pixels query dict.
    data = {
        "geom": {
            "type": "Feature",
            "crs": "EPSG:3857",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bounds[0], bounds[1]],
                    [bounds[2], bounds[1]],
                    [bounds[2], bounds[3]],
                    [bounds[0], bounds[3]],
                    [bounds[0], bounds[1]],
                ]]
            },
        },
        "scale": scale,
        "start": start,
        "end": end,
        "platform": const.PLATFORM_SENTINEL_2,
        "product_type": const.PRODUCT_L2A,
        "s2_max_cloud_cover_percentage": max_cloud_cover_percentage,
        "search_only": False,
        "composite": False,
        "latest_pixel": True,
        "color": True,
        "format": const.REQUEST_FORMAT_PNG,
    }
    return pixels(data)


@app.route('/wmts', methods=['GET'])
@token_required
def wmtsview():
    """
    WMTS endpoint with monthly latest pixel layers.
    """
    key = request.args.get('key')
    xml = wmts.gen(key, request.host_url)
    return Response(xml, mimetype="text/xml")
