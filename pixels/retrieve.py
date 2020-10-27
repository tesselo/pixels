import logging

import rasterio
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from pixels.const import NODATA_VALUE
from pixels.utils import compute_mask, compute_transform

logger = logging.getLogger(__name__)


def retrieve(source, geojson, scale=None, discrete=False, clip=False, all_touched=False, bands=None):
    """
    Get pixels from a source raster over the a geojson feature collection.
    """
    logger.info('Retrieving {}'.format(source))

    # Validate geojson by opening it with rasterio CRS class.
    dst_crs = CRS.from_dict(geojson['crs'])

    # Determine resampling algorithm.
    resampling = Resampling.nearest if discrete else Resampling.bilinear

    # Open remote raster.
    with rasterio.open(source) as src:
        # If no scale was provided, use the source scale as the target scale.
        if not scale:
            if src.crs and src.crs == dst_crs:
                scale = abs(src.transform[0])
            else:
                raise ValueError(
                    'Can not auto-determine target scale because'
                    'the geom crs does not match the source crs.'
                )

        # If no band indices were provided, process all bands.
        if not bands:
            bands = range(1, src.count + 1)

        # Prepare target raster transform from the geometry input.
        transform, width, height = compute_transform(geojson, scale)
        logger.info('Target array shape is ({}, {})'.format(height, width))

        # Prepare creation parameters for memory raster.
        creation_args = src.meta.copy()
        creation_args.update({
            'driver': 'GTiff',
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height,
        })

        # Open memory destination file.
        with MemoryFile() as memfile:
            with memfile.open(**creation_args) as dst:
                # Prepare projection arguments.
                proj_args = {
                    'dst_transform': transform,
                    'dst_crs': dst_crs,
                    'resampling': resampling,
                }

                # Determine georeferencing from source raster.
                if src.crs:
                    # Extract source crs directly.
                    src_crs = src.crs
                else:
                    # Extract georeference points and source crs from gcps.
                    # This is the case for Sentinel-1, for instance.
                    src_gcps, src_crs = src.gcps
                    proj_args['gcps'] = src.gcps[0]

                # Set source crs.
                proj_args['src_crs'] = src_crs

                # Transform raster bands from source to destination.
                for band in bands:
                    proj_args.update({
                        'source': rasterio.band(src, band),
                        'destination': rasterio.band(dst, band),
                    })
                    reproject(**proj_args)

                # Get pixel values of first band.
                pixels = dst.read(1)

                if clip:
                    mask = compute_mask(geojson, height, width, transform)
                    # Apply mask to all bands.
                    pixels[mask] = NODATA_VALUE

                # Return re-creation args and pixel data.
                return creation_args, pixels
