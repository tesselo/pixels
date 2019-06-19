import logging
import os
import pickle

import numpy
from rasterio.errors import RasterioIOError
from rasterio.io import MemoryFile

from pixels.const import (
    AWS_DATA_BUCKET_SENTINEL_1_L1C, AWS_DATA_BUCKET_SENTINEL_2_L1C, AWS_DATA_BUCKET_SENTINEL_2_L2A, MAX_PIXEL_SIZE,
    PLATFORM_SENTINEL_1, PROCESSING_LEVEL_S2_L1C, PRODUCT_L1C, SCENE_CLASS_INCLUDE, SCENE_CLASS_RANK_FLAT,
    SENTINEL_1_BANDS_HH_HV, SENTINEL_1_BANDS_VV, SENTINEL_1_BANDS_VV_VH, SENTINEL_1_POLARISATION_MODE,
    SENTINEL_2_BANDS, SENTINEL_2_DTYPE, SENTINEL_2_NODATA, SENTINEL_2_RESOLUTION_LOOKUP, SENTINEL_2_RGB_CLIPPER
)
from pixels.exceptions import PixelsFailed
from pixels.utils import choose, clone_raster, warp_from_s3

# Get logger.
logger = logging.getLogger(__name__)


def get_pixels(transform, width, height, crs, entry, bands=None):
    """
    Get pixel values from S3.
    """
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


def get_pixels_generator(transform, width, height, crs, entries, bands):
    """
    Get pixels from S3 incrementally.
    """
    for entry in entries:
        logger.info('Getting scene pixels for {}.'.format(entry['prefix']))
        yield get_pixels(transform, width, height, crs, entry, bands=bands)


def latest_pixel(transform, width, height, crs, data, bands=None):
    """
    Construct the latest pixel composite from the query result.

    Assumes single band rasters.
    """
    result = {}
    creation_args = None
    for entry in data:
        logger.info('Adding entry {} to latest pixel stack.'.format(entry['prefix']))
        try:
            data = get_pixels(transform, width, height, crs, entry, bands=bands)
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


def s2_composite_nn(transform, width, height, crs, entries, bands, product_type):
    """
    Compute a composite for a stack of S2 input data.
    """
    # Load cloud classifier. Legend: {'1': 'Clear', '2': 'Water', '3': 'Snow', '4': 'Shadow', '5': 'Cirrus', '6': 'Cloud'}
    if product_type == PRODUCT_L1C:
        clf_name = 'classifier-l1c.pickle'
    else:
        clf_name = 'classifier-694-l2a.pickle'

    with open(os.path.join(os.path.dirname(__file__), 'clf', clf_name), 'rb') as fl:
        clf = pickle.load(fl)

    # Convert rasters to numpy array.
    Xs = []
    # Prepare cloud probabilities holder and target rasterfile.
    cloud_probs = []
    raster_file_to_clone = None
    bands_present = None
    clone_creation_args = None
    # Compute cloud probabilities based on sen2cor sceneclass.
    for stack in get_pixels_generator(transform, width, height, crs, entries, bands):
        # Store creation args from first raster used, assuming all others are
        # identical.
        if clone_creation_args is None:
            with next(iter(stack.values())).open() as rst:
                clone_creation_args = rst.meta
        # Read raster files from this stack.
        data = {}
        for band, raster in stack.items():
            with raster.open() as rst:
                data[band] = rst.read().ravel()
        # Estimate cloud probablities for this stack.
        if product_type == PRODUCT_L1C:
            X = numpy.array([data[band] for band in SENTINEL_2_BANDS])
        else:
            X = numpy.array([data[band] for band in SENTINEL_2_BANDS if band != 'B10'])

        Yh = clf.predict_proba(X.T).T

        # Cloud probability is defined as P(shadow) + P(cirrus) + P(cloud)
        clouds = Yh[3] + Yh[4] + Yh[5]

        # Convert cloud probs to float.
        clouds = clouds.astype('float')

        # Set cloud prob high for nodata pixels.
        clouds[X[0] == SENTINEL_2_NODATA] = 999999

        cloud_probs.append(clouds)

        Xs.append(X)

        if raster_file_to_clone is None:
            raster_file_to_clone = stack['B04']
            bands_present = list(stack.keys())

    # Convert to numpy array.
    cloud_probs = numpy.array(cloud_probs)

    # Compute an array of scene indices with the lowest cloud probability.
    selector_index = numpy.argmin(cloud_probs, axis=0)

    # Loop over all bands.
    result = {}
    bands_present = [band for band in SENTINEL_2_BANDS if (product_type == PRODUCT_L1C or band != 'B10')]
    with raster_file_to_clone.open() as raster_to_clone:
        for i, band in enumerate(bands_present):
            # Merge scene tiles for this band into a composite tile using the selector index.
            bnds = [dat[i] for dat in Xs]
            # Construct final composite band array from selector index.
            composite_data = choose(selector_index, bnds).astype(SENTINEL_2_DTYPE)
            # Create band target raster.
            result[band] = clone_raster(raster_to_clone, composite_data)

    return result


def s2_composite_incremental_nn(transform, width, height, crs, entries, bands, product_type):
    """
    Compute composite with minimal effort, sequentially removing cloudy or
    shadow pixels.
    """
    # Load cloud classifier. Legend: {'1': 'Clear', '2': 'Water', '3': 'Snow', '4': 'Shadow', '5': 'Cirrus', '6': 'Cloud'}
    CLOUD_INDEX_CUTOFF = 0.5

    if product_type == PRODUCT_L1C:
        clf_name = 'classifier-l1c.pickle'
    else:
        clf_name = 'classifier-694-l2a.pickle'

    with open(os.path.join(os.path.dirname(__file__), 'clf', clf_name), 'rb') as fl:
        clf = pickle.load(fl)

    # Update target stack until all pixels.
    targets = {}
    clone_creation_args = None
    for stack in get_pixels_generator(transform, width, height, crs, entries, bands):
        # Store creation args from first raster used, assuming all others are
        # identical.
        if clone_creation_args is None:
            with next(iter(stack.values())).open() as rst:
                clone_creation_args = rst.meta
        # Read raster files from this stack.
        data = {}
        for band, raster in stack.items():
            with raster.open() as rst:
                data[band] = rst.read(1)
        # Construct data array for cloud prediction.
        if product_type == PRODUCT_L1C:
            X = numpy.array([data[band].ravel() for band in SENTINEL_2_BANDS])
        else:
            X = numpy.array([data[band].ravel() for band in SENTINEL_2_BANDS if band != 'B10'])
        # Estimate cloud probablities for this stack.
        Yh = clf.predict_proba(X.T).T
        # Cloud probability is defined as P(shadow) + P(cirrus) + P(cloud)
        cloud_probability_index = Yh[3] + Yh[4] + Yh[5]
        cloud_probability_index = cloud_probability_index.reshape((clone_creation_args['height'], clone_creation_args['width']))
        # Generate mask from exlude pixel class lookup.
        mask = cloud_probability_index < CLOUD_INDEX_CUTOFF
        # Update targets with this data using mask.
        for band, raster in data.items():
            if band in targets:
                # If targets already have data, update only empty pixels.
                band_mask = numpy.logical_and(mask, targets[band] == 0)
                targets[band][band_mask] = raster[band_mask]
            else:
                # Create new target array from raster.
                targets[band] = raster
                # Mask target array.
                targets[band][mask == 0] = 0

        # Check if all pixels have been populated using one of the target bands.
        if numpy.all(next(iter(targets.values())) > 0):
            break

    # Convert target arrays to rasterio memfiles.
    for band, data in targets.items():
        memfile = MemoryFile()
        # Set correct datatype.
        clone_creation_args['dtype'] = 'uint8' if band in ['SCL', 'NN6', 'NN1', 'NN2', 'NN3', 'NN4', 'NN5'] else 'uint16'
        # Create memfile raster.
        dst = memfile.open(**clone_creation_args)
        # Write result to raster.
        dst.write(data.reshape((1, clone_creation_args['height'], clone_creation_args['width'])))
        targets[band] = memfile

    return targets


def s2_color(stack, path=None):
    """
    Create RGB using the visual spectrum of an S2 stack.
    """
    data = numpy.array([
        stack['B04'].open().read(1),
        stack['B03'].open().read(1),
        stack['B02'].open().read(1),
    ])
    creation_args = stack['B04'].open().meta.copy()
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

    # Transform the data to provide an interpretable visual result.
    B0 *= 10
    B1 *= 10
    B0 = numpy.log(B0)
    B1 = numpy.log(B1)

    B0 = (B0 / 20) * SENTINEL_2_RGB_CLIPPER
    B1 = (B1 / 20) * SENTINEL_2_RGB_CLIPPER
    B2 = (B0 / B1) * 40

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


def s2_composite(transform, width, height, crs, entries, bands):
    """
    Compute a composite for a stack of S2 input data.
    """
    # Convert rasters to numpy array.
    Xs = []
    # Prepare cloud probabilities holder and target rasterfile.
    cloud_probs = []
    raster_file_to_clone = None
    bands_present = None
    # Compute cloud probabilities based on sen2cor sceneclass.
    for stack in get_pixels_generator(transform, width, height, crs, entries, bands):
        # Scene class pixels ranked by preference. The rank is flattened out so
        # that between categories that are similarly desireable, the relative NDVI
        # value is decisive.
        X = [raster.open().read(1) for raster in stack.values()]
        if 'SCL' in stack:
            # Use SCL layer to select pixel ranks.
            with stack['SCL'].open() as rst:
                scl = rst.read(1).astype(SENTINEL_2_DTYPE)
            clouds = choose(scl, SCENE_CLASS_RANK_FLAT)
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

        Xs.append(numpy.array(X))

        if raster_file_to_clone is None:
            raster_file_to_clone = stack['B04']
            bands_present = list(stack.keys())

    # If enough scenes are available, use the medioid over non-cloudy marked
    # pixels as selector.
    if len(Xs) >= 3:
        logger.info('Using medioid based calculation for composite.')
        for index, X in enumerate(Xs):
            # Compute sum of pairwise euclidian distances.
            pow = numpy.power([X.astype('float') - Xi.astype('float') for Xi in Xs], 2)
            dist = numpy.sum(pow, axis=(0, 1)) / len(Xs)
            # Add high distance for cloudy or shadow pixels.
            dist[cloud_probs[index] > 5] = 1e100 + cloud_probs[index][cloud_probs[index] > 5]
            # Override the cloud probability array with medioid based values.
            cloud_probs[index] = dist

    # Compute an array of scene indices with the lowest cloud probability.
    selector_index = numpy.argmin(numpy.array(cloud_probs), axis=0)

    # Loop over all bands.
    result = {}
    with raster_file_to_clone.open() as raster_to_clone:
        for i, band in enumerate(bands_present):
            # Merge scene tiles for this band into a composite tile using the selector index.
            bnds = [dat[i] for dat in Xs]
            # Construct final composite band array from selector index.
            composite_data = choose(selector_index, bnds).astype(SENTINEL_2_DTYPE)
            # Create band target raster.
            result[band] = clone_raster(raster_to_clone, composite_data)

    return result


def s2_composite_incremental(transform, width, height, crs, entries, bands):
    """
    Compute composite with minimal effort, sequentially removing cloudy or
    shadow pixels.
    """
    if 'SCL' not in bands:
        raise PixelsFailed('Only L2A for incremental mode.')

    # Update target stack until all pixels.
    targets = {}
    clone_creation_args = None
    for stack in get_pixels_generator(transform, width, height, crs, entries, bands):
        # Open raster files from this stack.
        data = {band: raster.open().read(1) for band, raster in stack.items()}
        # Generate mask from exlude pixel class lookup.
        mask = choose(data['SCL'], SCENE_CLASS_INCLUDE)
        # Update targets with this data using mask.
        for band, raster in data.items():
            if band in targets:
                # If targets already have data, update only empty pixels.
                band_mask = numpy.logical_and(mask, targets[band] == 0)
                targets[band][band_mask] = raster[band_mask]
            else:
                # Create new target array from raster.
                targets[band] = raster
                # Mask target array.
                targets[band][mask == 0] = 0

        # Store creation args from first raster used, assuming all others are
        # identical.
        if clone_creation_args is None:
            clone_creation_args = stack['SCL'].open().meta

        # Check if all pixels have been populated using one of the target bands.
        if numpy.all(targets['SCL'] > 0):
            break

    # Convert target arrays to rasterio memfiles.
    for band, data in targets.items():
        memfile = MemoryFile()
        # Set correct datatype.
        clone_creation_args['dtype'] = 'uint8' if band == 'SCL' else 'uint16'
        # Create memfile raster.
        dst = memfile.open(**clone_creation_args)
        # Write result to raster.
        dst.write(data.reshape((1, ) + data.shape))
        targets[band] = memfile

    return targets
