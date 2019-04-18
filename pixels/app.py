import copy
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
from flask import Flask, has_request_context, jsonify, redirect, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageEnhance
from pyproj import Proj, transform
from zappa.async import task

from pixels import const, scihub, search, utils

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


class PixelsFailed(Exception):
    """
    Custom exception.
    """
    status_code = 400

    def __init__(self, message, status_code=None, payload=None, tag=None):
        Exception.__init__(self)
        self.message = message
        self.tag = tag
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(PixelsFailed)
def handle_pixels_error(exc):
    response = jsonify(exc.to_dict())
    response.status_code = exc.status_code
    return response


@app.route('/', methods=['GET'])
@token_required
def index():
    return render_template('index.html')


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
    # Remove auth key from data dict.
    data.pop('key', None)
    # Limit size of geometry.
    # Transform the geom coordinates into web mercator and limit size
    # to 10km by 10km.
    src_srs = Proj(init=data['geom']['srs'])
    tar_srs = Proj(init='EPSG:3857')
    transformed_coords = [list(transform(src_srs, tar_srs, coord[0], coord[1])) for coord in data['geom']['geometry']['coordinates'][0]]
    dx = max(dat[0] for dat in transformed_coords) - min(dat[0] for dat in transformed_coords)
    dy = max(dat[1] for dat in transformed_coords) - min(dat[1] for dat in transformed_coords)
    area = abs(dx * dy)
    logger.info('Geometry area bbox is {:0.1f} km2.'.format(area / 1e6))
    MAX_AREA = 50000 ** 2
    if area > MAX_AREA:
        raise PixelsFailed('Input geometry bounding box area of {:0.1f} km2 is too large (max 100 km2).'.format(MAX_AREA / 1e6))

    # Reproject the geometry if in 4326.
    if data['geom']['srs'] == 'EPSG:4326':
        data['geom']['geometry']['coordinates'][0] = transformed_coords
        data['geom']['srs'] = 'EPSG:3857'

    # Get extract custom handler arguments.
    composite = data.pop('composite', False)
    latest_pixel = data.pop('latest_pixel', False)
    color = data.pop('color', False)
    bands = data.pop('bands', [])
    scale = data.pop('scale', 10)
    tag = data.pop('tag', None)
    delay = data.pop('delay', False)
    search_only = data.pop('search_only', False)
    clip_to_geom = data.pop('clip_to_geom', False)
    format = data.pop('format', const.REQUEST_FORMAT_ZIP).upper()

    # Comute render flag for convenience.
    render = format == const.REQUEST_FORMAT_PNG

    # Sanity checks.
    if format not in const.REQUEST_FORMATS:
        raise PixelsFailed('Request format {} not recognized. Use one of {}'.format(format, const.REQUEST_FORMATS))

    if not composite and not latest_pixel:
        raise PixelsFailed('Choose either latest pixel or composite mode.')

    if composite and data.get('platform', None) == const.PLATFORM_SENTINEL_1:
        raise PixelsFailed('Cannot compute composite for Sentinel 1.')

    if delay and search_only:
        raise PixelsFailed('Search only mode works in synchronous mode only.')

    # For composite, we will require all bands to be retrieved.
    if composite and not len(bands) == len(const.SENTINEL_2_BANDS):
        if data['product_type'] == const.PRODUCT_L2A:
            logger.info('Adding SCL for composite mode.')
            bands = list(set(bands + ['SCL']))
        else:
            logger.info('Adding all Sentinel-2 bands for composite mode.')
            bands = const.SENTINEL_2_BANDS

    # For color, assure the RGB bands are present.
    if render and data['platform'] == const.PLATFORM_SENTINEL_2:
        # For render, only request RGB bands.
        bands = const.SENTINEL_2_RGB_BANDS
    elif color and data['platform'] == const.PLATFORM_SENTINEL_2 and not all([dat in bands for dat in const.SENTINEL_2_RGB_BANDS]):
        logger.info('Adding RGB bands for color mode.')
        bands = list(set(bands + const.SENTINEL_2_RGB_BANDS))
    elif color and data['platform'] == const.PLATFORM_SENTINEL_1:
        # TODO: Allow other polarisation modes.
        bands = const.SENTINEL_1_POLARISATION_MODE['DV']
        bands = [band.lower() for band in bands]

    # Store original data and possible overrides.
    config_log = copy.deepcopy(data)
    config_log['composite'] = composite
    config_log['latest_pixel'] = latest_pixel
    config_log['color'] = color
    config_log['bands'] = bands
    config_log['scale'] = scale
    config_log['format'] = format
    config_log['search_only'] = search_only
    config_log['clip_to_geom'] = clip_to_geom
    logger.info('Configuration is {}'.format(config_log))

    # Handle delay mode.
    if delay:
        logger.info('Working in delay mode.')
        key = '{}/pixels.{}'.format(
            uuid.uuid4(),
            config_log['format'].lower(),
        )
        config_log['tag'] = key
        pixels_task(config_log)
        url = '{}async/{}?key={}'.format(request.host_url, key, request.args['key'])
        return jsonify(message='Getting pixels asynchronously. Your files will be ready at the link below soon.', url=url)
    else:
        # Only add delay flag here, otherwise this will trigger infinite loop.
        config_log['delay'] = True if tag else False

    # Query available scenery.
    logger.info('Querying data on the ESA SciHub.')
    query_result = search.search(**data)

    # Return only search query if requested.
    if search_only:
        return jsonify(query_result)

    if not len(query_result):
        raise PixelsFailed('No scenes found for the given search criteria.')

    # Get pixels.
    if latest_pixel:
        logger.info('Getting latest pixels stack.')
        stack = scihub.latest_pixel(data['geom'], query_result, scale=scale, bands=bands)
    else:
        for entry in query_result:
            logger.info('Getting scene pixels for {}.'.format(entry['prefix']))
            entry['pixels'] = scihub.get_pixels(data['geom'], entry, scale=scale, bands=bands)

        if composite:
            logger.info('Computing composite from pixel stacks.')
            stack = [entry['pixels'] for entry in query_result]
            stack = scihub.s2_composite(stack)

    # Clip to geometry if requested:
    if clip_to_geom:
        stack = utils.clip_to_geom(stack, data['geom'])

    # Convert to RGB color tif.
    if color:
        logger.info('Computing RGB image from stack.')
        if data.get('platform', None) == const.PLATFORM_SENTINEL_1:
            stack['RGB'] = scihub.s1_color(stack)
        else:
            stack['RGB'] = scihub.s2_color(stack)

        if render:
            logger.info('Rendering RGB data into PNG image.')
            pixpix = numpy.array([
                numpy.clip(stack['RGB'].open().read(1), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                numpy.clip(stack['RGB'].open().read(2), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                numpy.clip(stack['RGB'].open().read(3), 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
            ]).astype('uint8')

            # Create image object and enhance color scheme.
            img = Image.fromarray(pixpix.T)
            img = ImageEnhance.Contrast(img).enhance(1.1)
            img = ImageEnhance.Brightness(img).enhance(1.8)
            img = ImageEnhance.Color(img).enhance(1.3)

            # Save image to io buffer.
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            if tag:
                s3 = boto3.client('s3')
                s3.put_object(
                    Bucket=const.BUCKET,
                    Key=tag,
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
    if format == const.REQUEST_FORMAT_ZIP:
        logger.info('Packaging data into zip file.')
        with zipfile.ZipFile(bytes_buffer, 'w') as zf:
            # Write pixels into zip file.
            for key, raster in stack.items():
                raster.seek(0)
                zf.writestr('{}.tif'.format(key), raster.read())
            # Write config into zip file.
            zf.writestr('config.json', json.dumps(config_log))
    elif format == const.REQUEST_FORMAT_NPZ:
        logger.info('Packaging data into numpy npz file.')
        # Convert stack to numpy arrays.
        stack = {key: val.open().read(1) for key, val in stack.items()}
        # Save to compressed numpy npz format.
        numpy.savez_compressed(
            bytes_buffer,
            config=config_log,
            **stack
        )
    else:
        raise PixelsFailed('Unrecognized format {}, choose one of {}'.format(format, const.REQUEST_FORMATS))

    # Rewind buffer.
    bytes_buffer.seek(0)

    # Return buffer as file.
    if tag:
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=const.BUCKET,
            Key=tag,
            Body=bytes_buffer,
        )
    else:
        return send_file(
            bytes_buffer,
            as_attachment=True,
            attachment_filename='pixels.{}'.format(format.lower()),
            mimetype='application/{}'.format(format.lower())
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
        raise PixelsFailed('The minimal zoom level is 12.')
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
            "srs": "EPSG:3857",
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
