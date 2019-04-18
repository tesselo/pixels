import glob
import os
from math import ceil, pi

import numpy
import rasterio
from rasterio import Affine
from rasterio.features import bounds, rasterize
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from pixels import const


def filter_key(entry, namespace, key):
    """
    Extract a value from a section of a scihub entry namespace.
    """
    search_target = entry[namespace]
    if isinstance(search_target, dict):
        search_target = [search_target]
    return list(filter(lambda d: d['name'] == key, search_target))[0]['content']


def compute_transform(geom, scale):
    """
    Compute warp parameters from geometry. The scale is expected to be in the
    coordinate system units of the geometry.
    """
    extent = bounds(geom)
    transform = Affine(scale, 0, extent[0], 0, -scale, extent[3])
    width = ceil((extent[2] - extent[0]) / scale)
    height = ceil((extent[3] - extent[1]) / scale)

    return transform, width, height, geom['srs']


def tile_scale(z):
    """
    Calculate tile pixel size scale for given zoom level.
    """
    TILESIZE = 256
    WEB_MERCATOR_WORLDSIZE = 2 * pi * 6378137
    scale = WEB_MERCATOR_WORLDSIZE / 2.0 ** z / TILESIZE
    return round(scale, 8)


def warp_from_s3(bucket, prefix, transform, width, height, crs):
    """
    Warp a raster from S3 onto a local target raster using the target geotransform.
    """
    # Construct vsi path for the prefix.
    vsis3path = '/vsis3/{bucket}/{prefix}'.format(
        bucket=bucket,
        prefix=prefix,
    )

    # Open remote raster.
    with rasterio.open(vsis3path) as src:
        # Prepare creation parameters for memory raster.
        creation_args = src.meta.copy()
        creation_args.update({
            'driver': 'GTiff',
            'crs': crs,
            'transform': transform,
            'width': width,
            'height': height,
        })
        # Open memory destination file.
        memfile = MemoryFile()
        dst = memfile.open(**creation_args)
        # Prepare projection arguments.
        proj_args = {
            'dst_transform': transform,
            'dst_crs': crs,
            'resampling': Resampling.nearest,
        }

        if src.crs:
            # Extract source crs directly.
            src_crs = src.crs
        else:
            # Extract georeference points and source crs from gcps.
            src_gcps, src_crs = src.gcps
            proj_args['gcps'] = src.gcps[0]

        # Set source crs.
        proj_args['src_crs'] = src_crs

        # Transform raster bands from source to destination.
        for i in range(1, src.count + 1):
            proj_args.update({
                'src_crs': src_crs,
                'source': rasterio.band(src, i),
                'destination': rasterio.band(dst, i),
            })
            reproject(**proj_args)

        # Return memfile.
        memfile.seek(0)
        return memfile


def write_to_disk(rst, path):
    """
    Write a memory raster to disk.
    """
    with rasterio.open(path, 'w', **rst.meta.copy()) as dst:
        dst.write(rst.read())


def clone_raster(rst, data):
    """
    Clone a raster.
    """
    # Clone raster.
    creation_args = rst.meta.copy()
    memfile = MemoryFile()
    dst = memfile.open(**creation_args)

    # Write band data to target raster.
    dst.write(data.reshape((1, ) + (rst.height, rst.width)))

    # Return memfile object.
    return memfile


def persist(entry, folder):
    """
    Persist pixel data from an entry to a folder.
    """
    for band, val in entry['pixels'].items():
        write_to_disk(val, os.path.join(folder, '{}-{}-{}.tif'.format(entry['mgrs'], entry['date'].date(), band)))


def load_stacks(folder):
    """
    Load all persisted stacks from this folder.
    """
    stacks = {}
    for path in glob.glob(os.path.join(folder, '*.tif')):
        # mgrs, year, month, day, band = os.path.basename(path).split('.tif')[0].split('-')
        band, year, month, day, mgrs = os.path.basename(path).split('.tif')[0].split('-')
        key = '{}-{}-{}-{}'.format(mgrs, year, month, day)
        if key not in stacks:
            stacks[key] = {}
        stacks[key][band] = rasterio.open(path, 'r')
    return stacks


def tile_bounds(z, x, y):
    """
    Calculate the bounding box of a specific tile.
    """
    WEB_MERCATOR_WORLDSIZE = 2 * pi * 6378137

    WEB_MERCATOR_TILESHIFT = WEB_MERCATOR_WORLDSIZE / 2.0

    zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

    xmin = x * zscale - WEB_MERCATOR_TILESHIFT
    xmax = (x + 1) * zscale - WEB_MERCATOR_TILESHIFT
    ymin = WEB_MERCATOR_TILESHIFT - (y + 1) * zscale
    ymax = WEB_MERCATOR_TILESHIFT - y * zscale

    return [xmin, ymin, xmax, ymax]


def clip_to_geom(stack, geom):
    """
    Clip all rasters in this stack to the geometry.
    """
    # Compute mask from geom.
    with next(iter(stack.values())).open() as rst:
        mask = rasterize([geom['geometry']], out_shape=rst.shape, transform=rst.transform, all_touched=True).astype('bool')
    # If all pixels were included, return early.
    if numpy.all(mask):
        return stack
    # Invert mask to use for clipping rasters.
    mask = numpy.logical_not(mask)
    # Mask all rasters.
    result = {}
    for key, val in stack.items():
        with val.open() as rst:
            dat = rst.read(1)
            dat[mask] = const.SENTINEL_2_NODATA
            dat = dat.reshape((1, ) + dat.shape)
            result[key] = clone_raster(rst, dat)

    return result
