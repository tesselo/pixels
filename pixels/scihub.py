import logging

import numpy
from rasterio.errors import RasterioIOError
from rasterio.io import MemoryFile

from pixels.const import (
    AWS_DATA_BUCKET_SENTINEL_1_L1C, AWS_DATA_BUCKET_SENTINEL_2_L1C, AWS_DATA_BUCKET_SENTINEL_2_L2A, MAX_PIXEL_SIZE,
    PLATFORM_SENTINEL_1, PROCESSING_LEVEL_S2_L1C, SCENE_CLASS_RANK_FLAT, SENTINEL_1_BANDS_HH_HV, SENTINEL_1_BANDS_VV,
    SENTINEL_1_BANDS_VV_VH, SENTINEL_1_POLARISATION_MODE, SENTINEL_2_BANDS, SENTINEL_2_DTYPE, SENTINEL_2_NODATA,
    SENTINEL_2_RESOLUTION_LOOKUP, SENTINEL_2_RGB_CLIPPER
)
from pixels.exceptions import PixelsFailed
from pixels.utils import clone_raster, compute_transform, warp_from_s3

# Get logger.
logger = logging.getLogger(__name__)


def get_pixels(geom, entry, scale=10, bands=None):
    """
    Get pixel values from S3.
    """
    transform, width, height, crs = compute_transform(geom, scale=scale)
    # Sanity checks.
    if width > MAX_PIXEL_SIZE:
        raise PixelsFailed('Max raster width exceeded ({} > {}).'.format(width, MAX_PIXEL_SIZE))
    if height > MAX_PIXEL_SIZE:
        raise PixelsFailed('Max raster height exceeded ({} > {}).'.format(height, MAX_PIXEL_SIZE))

    if entry['platform_name'] == PLATFORM_SENTINEL_1:
        bucket = AWS_DATA_BUCKET_SENTINEL_1_L1C
        if not bands:
            bands = SENTINEL_1_POLARISATION_MODE[entry['polarisation_mode']]
            bands = [band.lower() for band in bands]
        band_prefix = entry['prefix'] + 'measurement/{}-{{}}.tiff'.format(entry['acquisition_mode'].lower())
    else:
        if entry['processing_level'] == PROCESSING_LEVEL_S2_L1C:
            bucket = AWS_DATA_BUCKET_SENTINEL_2_L1C
        else:
            bucket = AWS_DATA_BUCKET_SENTINEL_2_L2A

        if not bands:
            bands = SENTINEL_2_BANDS
        band_prefix = entry['prefix']

    result = {}
    for band in bands:
        if entry['platform_name'] == PLATFORM_SENTINEL_1:
            prefix = band_prefix.format(band.lower())
            print(prefix)
        elif entry['processing_level'] == PROCESSING_LEVEL_S2_L1C:
            prefix = band_prefix + '{}.jp2'.format(band)
        else:
            # Band 10 is not available in L2A.
            if band == 'B10':
                continue
            prefix = band_prefix + 'R{}m/{}.jp2'.format(SENTINEL_2_RESOLUTION_LOOKUP[band], band)

        result[band] = warp_from_s3(
            bucket=bucket,
            prefix=prefix,
            transform=transform,
            width=width,
            height=height,
            crs=crs,
        )

    return result


def latest_pixel(geom, data, scale=10, bands=None):
    """
    Construct the latest pixel composite from the query result.

    Assumes single band rasters.
    """
    result = {}
    creation_args = None
    for entry in data:
        logger.info('Adding entry {} to latest pixel stack.'.format(entry['prefix']))
        try:
            data = get_pixels(geom, entry, scale=scale, bands=bands)
        except RasterioIOError:
            # Catch error if a specific scene was not registered in S3 bucket.
            logger.warning('Not all bands found in S3 for scene key {}.'.format(entry['prefix']))
            continue
        # Save a copy of the creation arguments for later conversion to raster.
        if creation_args is None:
            with next(iter(data.values())).open() as tmp:
                creation_args = tmp.meta.copy()
        # Extract band arrays.
        array_entry = {key: val.open().read(1) for key, val in data.items()}
        # Prepare flag for remaining nodata pixels.
        has_remaining_empty_pixels = False
        # Parse additional pixels in a loop.
        for key, val in array_entry.items():
            if key in result:
                empty_pixels = result[key] == SENTINEL_2_NODATA
                new_pixels = val[empty_pixels]
                result[key][empty_pixels] = new_pixels
            else:
                new_pixels = val
                result[key] = new_pixels

            if numpy.any(new_pixels == SENTINEL_2_NODATA):
                has_remaining_empty_pixels = True

        if not has_remaining_empty_pixels:
            break

    rst_result = {}
    for key, val in result.items():
        memfile = MemoryFile()
        dst = memfile.open(**creation_args)
        dst.write(val.reshape((1, ) + val.shape).astype(SENTINEL_2_DTYPE))
        rst_result[key.upper()] = memfile

    return rst_result


def s2_composite(stacks):
    """
    Compute a composite for a stack of S2 input data.
    """
    # Convert rasters to numpy array.
    Xs = []
    # Prepare cloud probabilities holder.
    cloud_probs = []
    # Compute cloud probabilities based on sen2cor sceneclass.
    for stack in stacks:
        """
        Scene class pixels ranked by preference. The rank is flattened out so
        that between categories that are similarly desireable, the relative NDVI
        value is decisive.
        """
        X = [raster.open().read(1) for raster in stack.values()]
        if 'SCL' in stack:
            # Use SCL layer to select pixel ranks.
            with stack['SCL'].open() as rst:
                scl = rst.read(1).astype(SENTINEL_2_DTYPE)
            clouds = numpy.choose(scl, SCENE_CLASS_RANK_FLAT)
        else:
            # Prepare zeros cloud array.
            clouds = numpy.zeros(X[0].shape)

        # Get NDVI bands.
        with stack['B04'].open() as rst:
            B4 = rst.read(1).astype('float')
        with stack['B08'].open() as rst:
            B8 = rst.read(1).astype('float')

        # Compute NDVI, avoiding zero division for nodata pixels.
        ndvi_diff = B8 - B4
        ndvi_sum = B8 + B4
        ndvi_sum[ndvi_sum == SENTINEL_2_NODATA] = 1
        ndvi = ndvi_diff / ndvi_sum

        # Convert cloud probs to float.
        clouds = clouds.astype('float')

        # Add inverted and scaled NDVI values to the decimal range of the cloud
        # probs. This ensures that within acceptable pixels, the one with the
        # highest NDVI is selected.
        scaled_ndvi = (1 - ndvi) / 100
        clouds += scaled_ndvi

        # Set cloud prob high for nodata pixels.
        clouds[X[0] == SENTINEL_2_NODATA] = 999999

        cloud_probs.append(clouds)

        Xs.append(X)

    # Convert to numpy array.
    cloud_probs = numpy.array(cloud_probs)

    # Compute an array of scene indices with the lowest cloud probability.
    selector_index = numpy.argmin(cloud_probs, axis=0)

    # Loop over all bands.
    result = {}
    raster_file_to_clone = [val for key, val in stacks[0].items() if key != 'SCL'][0]
    with raster_file_to_clone.open() as raster_to_clone:
        for i, band in enumerate(stacks[0].keys()):
            # Merge scene tiles for this band into a composite tile using the selector index.
            bnds = numpy.array([dat[i] for dat in Xs])
            # Construct final composite band array from selector index.
            composite_data = numpy.choose(selector_index, bnds).astype(SENTINEL_2_DTYPE)
            # Create band target raster.
            result[band] = clone_raster(raster_to_clone, composite_data)

    return result


def s2_color(stack, path=None):
    """
    Create RGB using the visual spectrum of an S2 stack.
    """
    data = numpy.array([
        stack['B04'].open().read(1),
        stack['B03'].open().read(1),
        stack['B02'].open().read(1),
    ])
    if isinstance(stack['B04'], MemoryFile):
        creation_args = stack['B04'].open().meta.copy()
    else:
        creation_args = stack['B04'].meta.copy()

    creation_args['count'] = 3

    # Open memory destination file.
    memfile = MemoryFile()
    dst = memfile.open(**creation_args)
    dst.write(data)

    return memfile


def s1_color(stack, path=None):
    """
    Create RGB using the two S1 backscatter polarisation channels.
    """

    if SENTINEL_1_BANDS_VV[0] in stack:
        B0 = stack[SENTINEL_1_BANDS_VV_VH[0]]
        B1 = stack[SENTINEL_1_BANDS_VV_VH[1]]
    else:
        B0 = stack[SENTINEL_1_BANDS_HH_HV[0]]
        B1 = stack[SENTINEL_1_BANDS_HH_HV[1]]

    B0 = B0.open().read(1)
    B1 = B1.open().read(1)

    orig_dtype = B0.dtype

    B0 = 10 * numpy.log(B0)
    B1 = 10 * numpy.log(B1)
    B2 = (B0 / B1)

    B0 = (B0 - numpy.min(B0)) / (numpy.max(B0) - numpy.min(B0)) * SENTINEL_2_RGB_CLIPPER
    B1 = (B1 - numpy.min(B1)) / (numpy.max(B1) - numpy.min(B1)) * SENTINEL_2_RGB_CLIPPER
    B2 = (B2 - numpy.min(B2)) / (numpy.max(B2) - numpy.min(B2)) * SENTINEL_2_RGB_CLIPPER

    data = numpy.array([B0, B1, B2]).astype(orig_dtype)

    if isinstance(stack[SENTINEL_1_BANDS_VV_VH[0]], MemoryFile):
        creation_args = stack[SENTINEL_1_BANDS_VV_VH[0]].open().meta.copy()
    else:
        creation_args = stack[SENTINEL_1_BANDS_VV_VH[0]].meta.copy()

    creation_args['count'] = 3

    # Open memory destination file.
    memfile = MemoryFile()
    dst = memfile.open(**creation_args)
    dst.write(data)

    return memfile
