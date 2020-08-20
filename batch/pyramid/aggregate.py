import logging

import numpy
import rasterio
from rasterio import Affine
from rasterio.io import MemoryFile
from tile_range import tile_range

from pixels import algebra, const, utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# project_id='florence-s2'
project_id = 'clftests'
formula = '(B08-B04)/(B08+B04)'
zoom = 14
scale = utils.tile_scale(zoom)
tbounds = utils.tile_bounds(zoom, 4562, 6532)
geom = {
    'type': 'Feature',
    'crs': 'EPSG:3857',
    'geometry': {
        'type': 'Polygon',
        'coordinates': [[
            [tbounds[0], tbounds[1]],
            [tbounds[2], tbounds[1]],
            [tbounds[2], tbounds[3]],
            [tbounds[0], tbounds[3]],
            [tbounds[0], tbounds[1]],
        ]]
    },
}

result = []
for x, y, intersection in tile_range(geom, zoom, intersection=True, tolerance=10):
    print(const.BUCKET, project_id, zoom, x, y, formula)
    # Get pixels for all bands present in formula.
    data = {}
    for band in const.SENTINEL_2_BANDS:
        if band in formula:
            try:
                with rasterio.open('zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!{}.tif'.format(const.BUCKET, project_id, zoom, x, y, band)) as rst:
                    data[band] = rst.read(1).T.astype('float')
            except rasterio.errors.RasterioIOError:
                data = None
                break

    if not data:
        logger.warning('No data found for tile {} {} {}'.format(zoom, x, y))
        continue

    parser = algebra.FormulaParser()
    index = parser.evaluate(data, formula)

    width = 256
    height = 256
    scale_x = scale
    skew_x = 0.0
    origin_x = tbounds[0]
    skew_y = 0.0
    scale_y = -scale
    origin_y = tbounds[3]

    transform = Affine(scale_x, skew_x, origin_x, skew_y, scale_y, origin_y)

    creation_args = {
        'driver': 'GTiff',
        'crs': 'epsg:3857',
        'transform': transform,
        'width': width,
        'height': height,
        'dtype': 'float64',
        'count': 1,
    }

    # Get raster algebra from api destination.
    memfile = MemoryFile()
    with memfile.open(**creation_args) as dst:
        dst.write(index.reshape(1, height, width))
    memfile.seek(0)

    # Clip pixels to geom.
    clipped = utils.clip_to_geom({'index': memfile}, geom)['index']

    # Open pixels as array.
    with clipped.open() as clrst:
        result.append(clrst.read().ravel())

# Stack data.
result = numpy.hstack(result)

# Remove nan values.
result = result[numpy.logical_not(numpy.isnan(result))]

# Compute index stats from pixels.
stats = {
    'min': numpy.min(result),
    'max': numpy.max(result),
    'avg': numpy.mean(result),
    'std': numpy.nanstd(result),
    't0': len(result),
    't1': numpy.sum(result),
    't2': numpy.sum(numpy.square(result)),
}
print(stats)
