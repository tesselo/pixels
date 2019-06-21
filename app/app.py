import datetime
import functools
import json
import logging
import os
import tempfile
import uuid
import zipfile
from io import BytesIO

import boto3
import numpy
from dateutil import parser
from flask import Flask, Response, has_request_context, jsonify, redirect, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw
from rasterio import Affine
from rasterio.io import MemoryFile
from zappa.async import task

from app import utils as app_utils
from pixels import const, core, utils, wmts
from pixels.exceptions import PixelsFailed

# Flask setup
app = Flask(__name__)
app.config.from_pyfile('config.py')

# Logging setup
logger = logging.getLogger(__name__)

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
        if request.method == 'GET':
            # Look for a json string in data argument.
            data = json.loads(request.args['data'])
        else:
            # Retrieve json data from post request.
            data = request.get_json()

    # Validate input.
    config = utils.validate_configuration(data)

    # Handle delay mode.
    if config['delay'] and not config['tag']:
        logger.info('Working in delay mode.')
        # Add tag to config and call async task with tag specified.
        config['tag'] = utils.generate_unique_key(config['format'], ts_tag=config.get('base_path', ''), ts_tag_is_main_key='base_path' in config)
        print(config['tag'])
        url = '{}async/{}?key={}'.format(request.host_url, config['tag'], request.args['key'])
        pixels_task(config)
        return jsonify(message='Getting pixels asynchronously. Your files will be ready at the link below soon.', url=url)

    # Compute pixel stack.
    output = core.handler(config)

    # Return if no scenes could be found.
    if output is None:
        raise PixelsFailed('No scenes found for the given search criteria.')

    # Return search query if requested.
    if config['mode'] == const.MODE_SEARCH_ONLY:
        return jsonify(output)

    if config['tag']:
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=const.BUCKET,
            Key=config['tag'],
            Body=output,
        )
    elif config['color']:
        return send_file(output, mimetype='image/png')
    else:
        return send_file(
            output,
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
    except Exception as exc:
        s3 = boto3.client('s3')
        base = '/'.join(tag.split('/')[:-1])
        fail_result = {
            'error': str(exc),
            'data': data,
        }
        s3.put_object(
            Bucket=const.BUCKET,
            Key='{}/failed.json'.format(base),
            Body=json.dumps(fail_result).encode(),
        )
        raise


@app.route('/async/<tag>/<file>', methods=['GET'])
@app.route('/async/<basetag>/<tag>/<file>', methods=['GET'])
@token_required
def asyncresult(tag, file, basetag=None):
    """
    Retrieve an async result file.
    """
    logger.info('Looking for result object {}/{} from async call.'.format(tag, file))
    # Combine basetag with tag if present.
    if basetag:
        tag = basetag + '/' + tag
    # S3 client setup.
    s3 = boto3.resource('s3')
    obj = s3.Object(const.BUCKET, '{}/{}'.format(tag, file))
    # Get file, if not present, try getting fail json, if not present, its
    # still processing.
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
            failed = s3.Object(const.BUCKET, '{}/failed.json'.format(tag)).get()
        except s3.meta.client.exceptions.NoSuchKey:
            return jsonify(message='Async collection not finished yet.')
        else:
            return jsonify(message='Async collection falied.', data=json.loads(failed['Body'].read()))


@app.route('/tiles/<int:z>/<int:x>/<int:y>.png', methods=['GET'])
@app.route('/tiles/<platform>/<int:z>/<int:x>/<int:y>.png', methods=['GET'])
@token_required
def tiles(z, x, y, platform='s2'):
    """
    TMS tiles endpoint.
    """
    if z < const.PIXELS_MIN_ZOOM:
        path = os.path.dirname(os.path.abspath(__file__))
        # Open the ref image.
        img = Image.open(os.path.join(path, 'assets/tesselo_empty.png'))
        # Write zoom message into image.
        if z is not None:
            msg = 'Zoom is {} | Min zoom is {}'.format(z, const.PIXELS_MIN_ZOOM)
            draw = ImageDraw.Draw(img)
            text_width, text_height = draw.textsize(msg)
            draw.text(((img.width - text_width) / 2, 60 + (img.height - text_height) / 2), msg, fill='black')
        # Write image to response.
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return send_file(
            output,
            mimetype='image/png'
        )
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
        "mode": const.MODE_LATEST_PIXEL,
        "color": True,
        "format": const.REQUEST_FORMAT_PNG,
    }
    if platform.lower() == 's2':
        data.update({
            "platform": const.PLATFORM_SENTINEL_2,
            "product_type": const.PRODUCT_L2A,
            "max_cloud_cover_percentage": max_cloud_cover_percentage,
        })
    elif platform.lower() == 's1':
        data.update({
            "platform": const.PLATFORM_SENTINEL_1,
            "product_type": const.PRODUCT_GRD,
            's1_acquisition_mode': const.MODE_IW,
        })
    else:
        raise PixelsFailed('Platform "{}" not recognized, should be S1 or S2.'.format(platform))

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


@app.route('/timeseries', methods=['POST'])
@token_required
def timeseries():
    """
    Trigger computation of a timeseries dataset.
    """
    # Retrieve json data from post request.
    data = request.get_json()
    # Validate input.
    config = utils.validate_configuration(data)
    if 'interval' not in config:
        config['interval'] = const.TIMESERIES_MONTHLY
    if 'interval_step' not in config:
        config['interval_step'] = 1
    # Generate timeseries key.
    config['timeseries_tag'] = str(uuid.uuid4())
    # Loop through timesteps.
    results = []
    for here_start, here_end in utils.timeseries_steps(config['start'], config['end'], config['interval'], config['interval_step']):
        logger.info('Getting timeseries data from {} to {}.'.format(here_start, here_end))
        # Update config with intermediate timestamps.
        config.update({
            'start': str(here_start.date()),
            'end': str(here_end.date()),
        })
        # Generate unique key for target file and add download link to results.
        config['tag'] = utils.generate_unique_key(config['format'], config['timeseries_tag'])
        url = '{}async/{}?key={}'.format(request.host_url, config['tag'], request.args['key'])
        results.append({
            'start': str(here_start.date()),
            'end': str(here_end.date()),
            'url': url,
        })
        # Trigger async task.
        pixels_task(config)

    # Generate download url for the timeseries data.
    timeseries_url = '{}timeseries/{}/data.zip?key={}'.format(request.host_url, config['timeseries_tag'], request.args['key'])

    # Store the search results list as json at root of this timeseries.
    results_io = BytesIO(json.dumps(results).encode())
    results_io.seek(0)
    timeseries_json_key = '{}/ts_steps.json'.format(config['timeseries_tag'])

    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=const.BUCKET,
        Key=timeseries_json_key,
        Body=results_io,
    )

    # Return results list to user.
    return jsonify(
        message='Getting timeseries pixels asynchronously. Your files will be ready at the links below soon.',
        url=timeseries_url,
        timesteps=results,
    )


@app.route('/timeseries/<tag>/data.zip', methods=['GET'])
@token_required
def timeseries_result(tag):
    """
    Retrieve a timeseries dataset.
    """
    s3 = boto3.client('s3')

    # Check if result already exists.
    try:
        s3.get_object(Bucket=const.BUCKET, Key='{}/data.zip'.format(tag))
    except:
        pass
    else:
        url = boto3.client('s3').generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': const.BUCKET,
                'Key': '{}/data.zip'.format(tag),
            }
        )
        return redirect(url)

    # Get list of finished objects from target directory.
    results = s3.list_objects(Bucket=const.BUCKET, Prefix=tag)
    results = [dat['Key'] for dat in results['Contents'] if not dat['Key'].endswith('/ts_steps.json')]

    # Get the full timesteps list from the registry file.
    steps_key = '{tag}/ts_steps.json'.format(tag=tag)
    steps_file = s3.get_object(Bucket=const.BUCKET, Key=steps_key)
    steps = json.loads(steps_file['Body'].read())

    # Check if all pixels are collected.
    timesteps_count = len(steps)
    done_count = len(results)

    # Return with message if pixels are still being collected.
    if done_count != timesteps_count:
        return jsonify(
            message='Pixel collection not finished yet.'.format(done_count, timesteps_count),
            timesteps_done=done_count,
            timesteps_total=timesteps_count,
        )

    # Write all timesteps into a single zipfile.
    logger.info('Packaging data into zip file.')
    fl = tempfile.NamedTemporaryFile()
    with zipfile.ZipFile(fl.name, 'w') as zf:
        for step in steps:
            try:
                # Match step list json with existing objects search result.
                step_key = next(filter(lambda x: x in step['url'], results))
            except StopIteration:
                # Convert data target to fail json target. This ensures that for
                # fail cases, the error data json is included.
                fail_step_url = '/'.join(step['url'].split('/')[:-1]) + '/failed.json'
                step_key = next(filter(lambda x: x in fail_step_url, results))
            # Get file for match.
            step_file = s3.get_object(Bucket=const.BUCKET, Key=step_key)
            # Add datetime strings to file name.
            step_name = '{}_{}_{}'.format(step['start'], step['end'], step_key.split('/')[-1])
            # Add file to zip.
            zf.writestr(step_name, step_file['Body'].read())

    # Rewind and upload file to S3.
    fl.seek(0)
    s3.put_object(
        Bucket=const.BUCKET,
        Key='{}/data.zip'.format(tag),
        Body=fl,
    )
    # Redirect to file.
    url = boto3.client('s3').generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': const.BUCKET,
            'Key': '{}/data.zip'.format(tag),
        }
    )
    return redirect(url)


@app.route('/composite/<projectid>/<int:z>/<int:x>/<int:y>.<frmt>', methods=['GET'])
@token_required
def composite(projectid, z, x, y, frmt='png'):
    """
    Show tiles from TMS creation.
    """
    # Get formula.
    formula = request.args.get('formula', None)
    # Sanity checks.
    if frmt not in ['png', 'tif']:
        raise PixelsFailed('Format {} not recognized. Use png or tif.'.format(frmt))
    if frmt == 'tif' and not formula:
        raise PixelsFailed('Format TIF is only available for formula requests.')

    if formula:
        data = app_utils.get_s2_formula_pixels(
            projectid,
            z, x, y,
            formula,
            request.args.get('from', '00'),
            request.args.get('to', 'FF'),
            request.args.get('over', None),
            float(request.args.get('min', -1)),
            float(request.args.get('max', 1)),
            frmt,
        )
        mode = 'formula'
    else:
        # S2 Pixels.
        data = app_utils.get_s2_rgb_pixels(projectid, z, x, y)
        mode = 'S2'
        if not data:
            # S1 Pixels.
            data = app_utils.get_s1_rgb_pixels(projectid, z, x, y)
            mode = 'S1'

    if data is None:
        output = app_utils.get_empty_image(z)
    else:
        if formula:
            if frmt == 'tif':
                output = MemoryFile()
                scale = utils.tile_scale(z)
                tbounds = utils.tile_bounds(z, x, y)
                creation_args = {
                    'driver': 'GTiff',
                    'dtype': 'float',
                    'nodata': None,
                    'width': 256,
                    'height': 256,
                    'count': 1,
                    'crs': 'epsg:3857',
                    'transform': Affine(scale, 0.0, tbounds[0], 0.0, -scale, tbounds[3]),
                }
                with output.open(**creation_args) as dst:
                    dst.write(data.reshape(1, 256, 256))
                output.seek(0)
            else:
                pixpix = numpy.array(data, dtype='uint8')
                output = app_utils.get_image_from_pixels(pixpix, enhance=mode == 'S2')
        else:
            pixpix = numpy.array(
                [
                    numpy.clip(data[0], 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                    numpy.clip(data[1], 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                    numpy.clip(data[2], 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                    data[3],
                ],
                dtype='uint8',
            )
            output = app_utils.get_image_from_pixels(pixpix, enhance=mode == 'S2')

    return send_file(
        output,
        mimetype='image/{}'.format('png' if frmt == 'png' else 'tiff')
    )


@app.route('/composite/<projectid>/wmts', methods=['GET'])
@token_required
def composite_wmts(projectid):
    """
    WMTS endpoint for projects.
    """
    key = request.args.get('key')
    xml = wmts.gen_composite(key, request.host_url, projectid)
    return Response(xml, mimetype="text/xml")
