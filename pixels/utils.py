import math

from dateutil import parser
from dateutil.relativedelta import relativedelta
from fiona.transform import transform
from rasterio import Affine
from rasterio.features import bounds, rasterize


def compute_transform(geojson, scale):
    """
    Compute warp parameters from geometry. The scale is expected to be in the
    coordinate system units of the geometry.
    """
    extent = bounds(geojson)
    transform = Affine(scale, 0, extent[0], 0, -scale, extent[3])
    width = math.ceil((extent[2] - extent[0]) / scale)
    height = math.ceil((extent[3] - extent[1]) / scale)

    return transform, width, height


def compute_mask(geojson, height, width, transform, value_column_name=None, all_touched=False):
    """
    Compute geometry mask. If specified, the burn value for each geometry will
    be used from the value_column_name.
    """
    # Create a list of geometries, if requested with a burn value.
    if value_column_name:
        geoms_to_rasterize = [(dat['geometry'], dat['properties'][value_column_name]) for dat in geojson['features']]
    else:
        geoms_to_rasterize = [dat['geometry'] for dat in geojson['features']]

    # Rasterize the geoms.
    mask = rasterize(
        geoms_to_rasterize,
        out_shape=(height, width),
        transform=transform,
        all_touched=all_touched,
        default_value=0,
        fill=1,
    )
    # Convert to boolean mask if no value column has been specified.
    if not value_column_name:
        mask = mask.astype('bool')

    return mask


def compute_wgs83_bbox(geojson):
    """
    Computes the bounding box of the input geojson in WGS84 coordinates.
    """
    # Compute bounding box in original coordinates.
    bbox = bounds(geojson)
    # Transform the two corners.
    crs = geojson['crs']['init'] if 'init' in geojson['crs'] else geojson['crs']['properties']['name']
    corners = transform(crs, 'EPSG:4326', [bbox[0], bbox[2]], [bbox[1], bbox[3]])
    # Compute transformed range.
    xmin = min(corners[0])
    ymin = min(corners[1])
    xmax = max(corners[0])
    ymax = max(corners[1])
    # Return new bounding box as geojson polygon.
    return {
        "type": "Polygon",
        "coordinates": [[
            [xmin, ymin],
            [xmin, ymax],
            [xmax, ymax],
            [xmax, ymin],
            [xmin, ymin],
        ]],
    }


def timeseries_steps(start, end, interval, intervals_per_step=1):
    """
    Construct a series of timestep intervals given the input date range.
    """
    # Convert input to dates if provided as str.
    if isinstance(start, str):
        start = parser.parse(start)
    if isinstance(end, str):
        end = parser.parse(end)
    # Compute time delta.
    delta = relativedelta(**{interval.lower(): int(intervals_per_step)})
    one_day = relativedelta(days=1)
    # Create intermediate timestamps.
    here_start = start
    here_end = start + delta
    # Loop through timesteps.
    while (here_end - one_day) <= end:
        yield here_start.date(), (here_end - one_day).date()
        # Increment intermediate timestamps.
        here_start += delta
        here_end += delta


def extract_crs(geojson):
    bytes_geojson = io.BytesIO(bytes(json.dumps(geojson), encoding='utf8'))
    with fiona.open(bytes_geojson, driver='GeoJSON') as fiona_geojson:
        return CRS.from_dict(fiona_geojson.crs)
