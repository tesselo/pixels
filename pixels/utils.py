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


def compute_wgs83_bbox(geojson, return_bbox=False):
    """
    Computes the bounding box of the input geojson in WGS84 coordinates.
    """
    # Compute bounding box in original coordinates.
    bbox = bounds(geojson)

    # Transform the two corners.
    crs = geojson['crs']['init'] if 'init' in geojson['crs'] else geojson['crs']['properties']['name']
    if 'EPSG:4326' not in crs:
        bbox = transform(crs, 'EPSG:4326', [bbox[0], bbox[2]], [bbox[1], bbox[3]])

    # Compute transformed range.
    xmin = min(bbox[0])
    ymin = min(bbox[1])
    xmax = max(bbox[0])
    ymax = max(bbox[1])

    if return_bbox:
        bbox = (xmin, ymin, xmax, ymax)
    else:
        # Return new bounding box as geojson polygon.
        bbox = {
            "type": "Polygon",
            "coordinates": [[
                [xmin, ymin],
                [xmin, ymax],
                [xmax, ymax],
                [xmax, ymin],
                [xmin, ymin],
            ]],
        }

    return bbox


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
