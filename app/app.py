import datetime
import functools
import os

import mercantile
import numpy
import rasterio
from flask import (
    Flask,
    Response,
    has_request_context,
    jsonify,
    render_template,
    request,
    send_file,
)
from flask_sqlalchemy import SQLAlchemy

from app import const, wmts
from app.errors import PixelsAuthenticationFailed
from pixels.mosaic import latest_pixel

# Flask setup
app = Flask(__name__)
app.config.from_pyfile("config.py")

# DB Setup
db = SQLAlchemy(app)


class RasterApiReadonlytoken(db.Model):
    key = db.Column(db.String(40), primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    created = db.Column(db.DateTime)

    def __repr__(self):
        return "Token %r" % self.key


def token_required(func):
    """
    Decorator to check for auth token.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Only run the test if the function is called as a view.
        if has_request_context():
            if request.host != "127.0.0.1:5000":
                key = request.args.get("key", None)
                if not key:
                    raise PixelsAuthenticationFailed("Authentication key is required.")
                token = RasterApiReadonlytoken.query.get(key)
                if not token:
                    raise PixelsAuthenticationFailed("Authentication key is not valid.")
        return func(*args, **kwargs)

    return wrapper


@app.errorhandler(PixelsAuthenticationFailed)
def handle_pixels_error(exc):
    response = jsonify(exc.to_dict())
    response.status_code = exc.status_code
    return response


@app.route("/", methods=["GET"])
@token_required
def index():
    return render_template("index.html")


@app.route("/docs", methods=["GET"])
@token_required
def docs():
    return render_template("docs.html")


@app.route("/wmts", methods=["GET"])
@token_required
def wmtsview():
    """
    WMTS endpoint with monthly latest pixel layers.
    """
    key = request.args.get("key")
    max_cloud_cover_percentage = request.args.get("max_cloud_cover_percentage", 100)
    xml = wmts.gen(key, request.host_url, max_cloud_cover_percentage)
    return Response(xml, mimetype="text/xml")


@app.route("/tiles/<int:z>/<int:x>/<int:y>.png", methods=["GET"])
@app.route("/tiles/<platform>/<int:z>/<int:x>/<int:y>.png", methods=["GET"])
@token_required
def tiles(z, x, y, platform=None):
    """
    TMS tiles endpoint.
    """
    # Check for minimum zoom.
    if z < const.PIXELS_MIN_ZOOM:
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, "assets/tesselo_zoom_in_more.png")
        return send_file(open(path, "rb"), mimetype="image/png")

    # Retrieve end date from query args.
    end = request.args.get("end")
    if not end:
        end = str(datetime.datetime.now().date())
    # Get cloud cover filter.
    max_cloud_cover_percentage = int(
        request.args.get("max_cloud_cover_percentage", 100)
    )
    # Compute tile bounds and scale.
    bounds = mercantile.xy_bounds(x, y, z)
    scale = abs(bounds[3] - bounds[1]) / const.TILE_SIZE
    geojson = {
        "type": "FeatureCollection",
        "crs": {"init": "EPSG:3857"},
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [bounds[0], bounds[1]],
                            [bounds[2], bounds[1]],
                            [bounds[2], bounds[3]],
                            [bounds[0], bounds[3]],
                            [bounds[0], bounds[1]],
                        ]
                    ],
                },
            }
        ],
    }
    # Specify the platform to use.
    if platform == "landsat_7" or end < "2014-01-01":
        platform = "LANDSAT_7"
        bands = ["B3", "B2", "B1"]
        scaling = 256
    elif platform == "landsat_8" or end < "2018-01-01":
        platform = "LANDSAT_8"
        bands = ["B4", "B3", "B2"]
        scaling = 30000
    else:
        platform = "SENTINEL_2"
        bands = ["B04", "B03", "B02"]
        scaling = 4000
    # Get pixels.
    creation_args, date, stack = latest_pixel(
        geojson,
        end,
        scale,
        bands=bands,
        platforms=[platform],
        limit=10,
        clip=False,
        pool=False,
        maxcloud=max_cloud_cover_percentage,
    )
    # Convert stack to image array in uint8.
    img = numpy.array(
        [255 * (numpy.clip(dat, 0, scaling) / scaling) for dat in stack]
    ).astype("uint8")
    # Prepare PNG outpu parameters.
    creation_args.update(
        {
            "driver": "PNG",
            "dtype": "uint8",
            "count": 3,
        }
    )
    # Write data to PNG memfile.
    memfile = rasterio.io.MemoryFile()
    with memfile.open(**creation_args) as dst:
        dst.write(img)
    memfile.seek(0)
    # Send file.
    return send_file(memfile, mimetype="image/png")
