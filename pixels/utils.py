import glob
import os
from math import ceil, pi

import rasterio
from rasterio import Affine
from rasterio.features import bounds
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject


def filter_key(entry, namespace, key):
    """
    Extract a value from a section of a scihub entry namespace.
    """
    return list(filter(lambda d: d['name'] == key, entry[namespace]))[0]['content']


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


def warp_from_s3(bucket, prefix, transform, width, height, crs, as_array=False, as_file=False):
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

        # Extract band arrays if requested.
        if as_array:
            return [dst.read(i) for i in range(1, dst.count + 1)]
        elif as_file:
            memfile.seek(0)
            return memfile
        else:
            return dst


def write_to_disk(rst, path):
    """
    Write a memory raster to disk.
    """
    with rasterio.open(path, 'w', **rst.meta.copy()) as dst:
        dst.write(rst.read())


def clone_raster(rst, data, as_file=False):
    """
    Clone a raster.
    """
    # Clone raster.
    creation_args = rst.meta.copy()
    memfile = MemoryFile()
    dst = memfile.open(**creation_args)

    # Write band data to target raster.
    dst.write(data.reshape((1, ) + (rst.height, rst.width)))

    # Return raster or file object.
    if as_file:
        return memfile
    else:
        return dst


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
