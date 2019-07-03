import logging

import rasterio
from shapely.geometry import Polygon, shape

from pixels import utils

# Get logger.
logger = logging.getLogger(__name__)


def tile_range(geom, zoom, intersection=False, tolerance=0):
    """
    Compute tile range of TMS tiles intersecting with the input geometry at the
    given zoom level.
    """
    # Compute general tile bounds.
    geombounds = rasterio.features.bounds(utils.reproject_feature(geom, 'EPSG:4326'))
    minimumTile = utils.tile_index(geombounds[0], geombounds[3], zoom)
    maximumTile = utils.tile_index(geombounds[2], geombounds[1], zoom)
    logger.info('Tile range is {} - {}'.format(minimumTile, maximumTile))

    # Convert geometry to shape.
    geom_shape = shape(utils.reproject_feature(geom, 'EPSG:3857')['geometry'])

    # Loop through all tiles but only yeald the intersecting ones.
    for x in range(minimumTile[0], maximumTile[0] + 1):
        for y in range(minimumTile[1], maximumTile[1] + 1):

            # Compute tile bounds.
            tbounds = utils.tile_bounds(zoom, x, y)

            if tolerance:
                tbounds[0] += tolerance
                tbounds[2] += tolerance
                tbounds[1] -= tolerance
                tbounds[3] -= tolerance

            # Instanciate tile polygon.
            tile = Polygon([
                [tbounds[0], tbounds[1]],
                [tbounds[2], tbounds[1]],
                [tbounds[2], tbounds[3]],
                [tbounds[0], tbounds[3]],
                [tbounds[0], tbounds[1]],
            ])

            # Yield tile index if the tile intersects with the geometry. Also
            # include tile intersection geometry if requested.
            if intersection:
                tile_intersection = tile.intersection(geom_shape)
                if tile_intersection:
                    yield x, y, tile_intersection
            elif tile.intersects(geom_shape):
                yield x, y
