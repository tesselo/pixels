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
import rasterio
from dateutil import parser
from flask import Flask, Response, has_request_context, jsonify, redirect, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageEnhance
from zappa.async import task

from pixels import algebra, const, core, utils, wmts
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


def hex_to_rgba(value, alpha=255):
    """
    Converts a HEX color string to a RGBA 4-tuple.
    """
    if value is None:
        return [None, None, None]

    value = value.lstrip('#')

    # Check length and input string property
    if len(value) not in [1, 2, 3, 6] or not value.isalnum():
        raise PixelsFailed('Invalid color, could not convert hex to rgb.')

    # Repeat values for shortened input
    value = (value * 6)[:6]

    # Convert to rgb
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def rescale_to_channel_range(data, dfrom, dto, dover=None):
    """
    Rescales an array to the color interval provided. Assumes that the data is normalized.
    This is used as a helper function for continuous colormaps.
    """
    # If the interval is zero dimensional, return constant array.
    if dfrom == dto:
        return numpy.ones(data.shape) * dfrom

    if dover is None:
        # Invert data going from smaller to larger if origin color is bigger
        # than target color.
        if dto < dfrom:
            data = 1 - data
        return data * abs(dto - dfrom) + min(dto, dfrom)
    else:
        # Divide data in upper and lower half.
        lower_half = data < 0.5
        # Recursive calls to scaling upper and lower half separately.
        data[lower_half] = rescale_to_channel_range(data[lower_half] * 2, dfrom, dover)
        data[numpy.logical_not(lower_half)] = rescale_to_channel_range((data[numpy.logical_not(lower_half)] - 0.5) * 2, dover, dto)

    return data


@app.route('/composite/<projectid>/<int:z>/<int:x>/<int:y>.png', methods=['GET'])
@token_required
def composite(projectid, z, x, y):
    """
    Show tiles from TMS creation.
    """
    return_empty = False
    sentinel_1 = False
    # Look for a json string in data argument.
    formula = request.args.get('formula', None)
    if formula and not return_empty:
        parser = algebra.FormulaParser()
        data = {}
        for band in const.SENTINEL_2_BANDS:
            if band in formula:
                try:
                    with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!{}.tif'.format(const.BUCKET, projectid, z, x, y, band)) as rst:
                        data[band] = rst.read(1).T.astype('float')
                except rasterio.errors.RasterioIOError:
                    return_empty = True

        if not return_empty:
            index = parser.evaluate(data, formula)

            dmin = float(request.args.get('min', -1))
            dmax = float(request.args.get('max', 1))

            if dmax == dmin:
                norm = index == dmin
            else:
                norm = (index - dmin) / (dmax - dmin)

            color_from = hex_to_rgba(request.args.get('from', '00'))
            color_to = hex_to_rgba(request.args.get('to', 'FF'))
            color_over = hex_to_rgba(request.args.get('over', None))

            red = rescale_to_channel_range(norm.copy(), color_from[0], color_to[0], color_over[0])
            green = rescale_to_channel_range(norm.copy(), color_from[1], color_to[1], color_over[1])
            blue = rescale_to_channel_range(norm.copy(), color_from[2], color_to[2], color_over[2])

            # Compute alpha channel from mask if available.
            alpha = numpy.all([dat != 0 for dat in data.values()], axis=0) * 255

            pixpix = numpy.array([red, green, blue, alpha], dtype='uint8')
    else:
        try:
            with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!B04.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                red = rst.read(1)
            with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!B03.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                green = rst.read(1)
            with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!B02.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                blue = rst.read(1)
            mask = numpy.all((red != 0, blue != 0, green != 0), axis=0).T * 255
        except rasterio.errors.RasterioIOError:
            try:
                with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!VV.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                    red = rst.read(1)
                with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!VH.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                    green = rst.read(1)
            except rasterio.errors.RasterioIOError:
                try:
                    with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!HH.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                        red = rst.read(1)
                    with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!HV.tif'.format(const.BUCKET, projectid, z, x, y)) as rst:
                        green = rst.read(1)
                except:
                    return_empty = True
            if not return_empty:
                mask = numpy.all((red != 0, green != 0), axis=0).T * 255

                # Transform the data to provide an interpretable visual result.
                red = numpy.log(red)
                green = numpy.log(green)

                red = (red / 7) * const.SENTINEL_2_RGB_CLIPPER
                green = (green / 7) * const.SENTINEL_2_RGB_CLIPPER
                blue = (red / green) * const.SENTINEL_2_RGB_CLIPPER / 2

                sentinel_1 = True

        if not return_empty:
            pixpix = numpy.array(
                [
                    numpy.clip(red, 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                    numpy.clip(green, 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                    numpy.clip(blue, 0, const.SENTINEL_2_RGB_CLIPPER).T * 255 / const.SENTINEL_2_RGB_CLIPPER,
                    mask,
                ],
                dtype='uint8',
            )

    output = BytesIO()
    if return_empty:
        path = os.path.dirname(os.path.abspath(__file__))
        # Open the ref image.
        img = Image.open(os.path.join(path, 'assets/tesselo_empty.png'))
        # Write zoom message into image.
        if z > 14:
            msg = 'Zoom is {} | Max zoom is 14'.format(z)
        else:
            msg = 'No Data'
        draw = ImageDraw.Draw(img)
        text_width, text_height = draw.textsize(msg)
        draw.text(((img.width - text_width) / 2, 60 + (img.height - text_height) / 2), msg, fill='black')
        # Save image to io buffer.
        img.save(output, format='PNG')
    else:
        # Create image object.
        img = Image.fromarray(pixpix.T)
        # Enhance color scheme for RGB mode.
        if not formula and not sentinel_1:
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Brightness(img).enhance(1.8)
            img = ImageEnhance.Color(img).enhance(1.4)

        # Save image to io buffer.
        img.save(output, format=const.REQUEST_FORMAT_PNG)

    output.seek(0)
    return send_file(
        output,
        mimetype='image/png'
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
