import pickle

import numpy
from rasterio.io import MemoryFile

from pixels.const import (AWS_DATA_BUCKET_SENTINEL_1_L1C,
                          AWS_DATA_BUCKET_SENTINEL_2_L1C,
                          AWS_DATA_BUCKET_SENTINEL_2_L2A, PLATFORM_SENTINEL_1,
                          PROCESSING_LEVEL_S2_L1C, SENTINEL_1_BANDS_HH_HV,
                          SENTINEL_1_BANDS_VV, SENTINEL_1_BANDS_VV_VH,
                          SENTINEL_1_POLARISATION_MODE, SENTINEL_2_BANDS,
                          SENTINEL_2_NODATA)
from pixels.utils import clone_raster, compute_transform, warp_from_s3
from sen2cor.sceneclass import SceneClass


def get_pixels(geom, entry, scale=10, bands=None, as_array=False, as_file=False):
    """
    Get pixel values from S3.
    """
    transform, width, height, crs = compute_transform(geom, scale=scale)

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
        band_prefix = entry['prefix'] + '{}.jp2'

    result = {}
    for band in bands:
        result[band] = warp_from_s3(
            bucket=bucket,
            prefix=band_prefix.format(band),
            transform=transform,
            width=width,
            height=height,
            crs=crs,
            as_array=as_array,
            as_file=as_file,
        )

    return result


def latest_pixel(geom, data, scale=10, bands=None, as_array=False, as_file=False):
    """
    Construct the latest pixel composite from the query result.

    Assumes single band rasters.
    """
    result = {}
    creation_args = None
    for entry in data:
        print('Adding entry', entry['prefix'], 'to latest pixel stack.')
        data = get_pixels(geom, entry, scale=scale, bands=bands)
        # Save a copy of the creation arguments for later conversion to raster.
        if creation_args is None:
            creation_args = next(iter(data.values())).meta.copy()
        # Extract band arrays.
        array_entry = {key: val.read(1) for key, val in data.items()}
        # Prepare flag for remaining nodata pixels.
        has_remaining_empty_pixels = False
        # Parse additional pixels in a loop.
        for key, val in array_entry.items():
            if key in result:
                empty_pixels = result[key].read(1) == SENTINEL_2_NODATA
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
        dst.write(val.reshape((1, ) + val.shape))
        # Convert to numpy array or set file if requested.
        if as_array:
            dst = [dst.read(i) for i in range(1, dst.count + 1)]
        elif as_file:
            dst = memfile

        rst_result[key.upper()] = dst

    return rst_result


def s2_composite(stacks, index_based=True, as_file=False):
    """
    Compute a composite for a stack of S2 input data.
    """
    # Cloud Extraction Indices, these are range indices for 2d arrays that are
    # needed to extract values by index when doing the cloud removal.
    width = stacks[0]['B02'].width
    height = stacks[0]['B02'].height
    CLOUD_IDX1, CLOUD_IDX2 = numpy.indices((width, height))
    # Convert rasters to numpy array.
    Xs = []
    for stack in stacks:
        Xs.append([stack[band].read(1) for band in SENTINEL_2_BANDS])

    # Predict class probabilities from classifier, normalized to sensor range.
    if index_based:
        # Prepare cloud probabilities holder.
        cloud_probs = []
        # Compute cloud probabilities based on sen2cor sceneclass.
        for X in Xs:
            """
            Scene class pixels ranked by preference. The rank is flattened out so
            that between categories that are similarly desireable, the relative NDVI
            value is decisive.
            """
            sc = SceneClass(X, solaz=0, solze=0.5)
            sc.process()

            SCENE_CLASS_RANK_FLAT = (
                8,   # NO_DATA
                7,   # SATURATED_OR_DEFECTIVE
                5,   # DARK_AREA_PIXELS
                5,   # CLOUD_SHADOWS
                1,   # VEGETATION
                2,   # NOT_VEGETATED
                3,   # WATER
                5,   # UNCLASSIFIED
                6,   # CLOUD_MEDIUM_PROBABILITY
                7,   # CLOUD_HIGH_PROBABILITY
                6,   # THIN_CIRRUS
                4,   # SNOW
            )

            # Use SCL layer to select pixel ranks.
            clouds = numpy.choose(sc.result.astype('int'), SCENE_CLASS_RANK_FLAT)

            # Convert cloud probs to float.
            clouds = clouds.astype('float')

            # Compute NDVI, avoiding zero division.
            B4 = X[3].astype('float')  # B04
            B8 = X[7].astype('float')  # B08
            ndvi_diff = B8 - B4
            ndvi_sum = B8 + B4
            ndvi_sum[ndvi_sum == SENTINEL_2_NODATA] = 1
            ndvi = ndvi_diff / ndvi_sum

            # Add inverted and scaled NDVI values to the decimal range of the cloud
            # probs. This ensures that within acceptable pixels, the one with the
            # highest NDVI is selected.
            scaled_ndvi = (1 - ndvi) / 100
            clouds += scaled_ndvi

            # Set cloud prob high for nodata pixels.
            clouds[X[3] == SENTINEL_2_NODATA] = 999999

            cloud_probs.append(clouds)
    else:
        Xs = numpy.array(Xs)
        # Load cloud classifier.
        clf = pickle.loads(open('/home/tam/Desktop/sklearn_mlc_clouds.pickle', 'rb').read())
        # Create class name lookup.
        class_names = {
            'Clear': 10,
            'Water': 20,
            'Shadow': 30,
            'Cirrus': 40,
            'Cloud': 50,
            'Snow': 60,
        }
        # Compute cloud colunm indices from classifier.
        cloud_idx = numpy.where(clf.classes_ == class_names['Cloud'])[0][0]
        cirrus_idx = numpy.where(clf.classes_ == class_names['Cirrus'])[0][0]
        shadow_idx = numpy.where(clf.classes_ == class_names['Shadow'])[0][0]

        clouds_and_shadows_idx = [cloud_idx, cirrus_idx, shadow_idx]

        Ys = []
        for X in Xs:
            Y = []
            for batch in numpy.array_split(X, X.shape[1] / 1000, axis=1):
                Y.append(clf.predict_proba(batch.T / 1e4))
            Ys.append(numpy.vstack(Y))
        Ys = numpy.array(Ys)

        # Compute the consolidated cloud probabilities for each avaiable scene band stack.
        cloud_probs = []
        for i, Y in enumerate(Ys):
            prob = numpy.sum(Y[:, clouds_and_shadows_idx], axis=1)
            # Set cloud prob high for nodata pixels.
            prob[Xs[i][0] == SENTINEL_2_NODATA] = 999
            cloud_probs.append(prob)

    # Convert to numpy array.
    cloud_probs = numpy.array(cloud_probs)

    # Compute an array of scene indices with the lowest cloud probability.
    selector_index = numpy.argmin(cloud_probs, axis=0)

    # Loop over all bands.
    result = {}
    for i, band in enumerate(SENTINEL_2_BANDS):
        # Merge scene tiles for this band into a composite tile using the selector index.
        bnds = numpy.array([X[i] for X in Xs])
        # Construct final composite band array from selector index.
        composite_data = numpy.choose(selector_index, bnds)
        # Create band target raster.
        result[band] = clone_raster(next(iter(stacks[0].values())), composite_data, as_file=as_file)

    return result


def s2_color(stack, path=None, as_file=False):
    """
    Create RGB using the visual spectrum of an S2 stack.
    """
    data = numpy.array([
        stack['B04'].open().read(1) if isinstance(stack['B04'], MemoryFile) else stack['B04'].read(1),
        stack['B03'].open().read(1) if isinstance(stack['B03'], MemoryFile) else stack['B03'].read(1),
        stack['B02'].open().read(1) if isinstance(stack['B02'], MemoryFile) else stack['B02'].read(1),
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
    if as_file:
        return memfile
    else:
        return dst


def s1_color(stack, path=None, as_file=False):
    """
    Create RGB using the two S1 backscatter polarisation channels.
    """

    if SENTINEL_1_BANDS_VV[0] in stack:
        B0 = stack[SENTINEL_1_BANDS_VV_VH[0]]
        B1 = stack[SENTINEL_1_BANDS_VV_VH[1]]
    else:
        B0 = stack[SENTINEL_1_BANDS_HH_HV[0]]
        B1 = stack[SENTINEL_1_BANDS_HH_HV[1]]

    B0 = B0.open().read(1) if isinstance(B0, MemoryFile) else B0.read(1)
    B1 = B1.open().read(1) if isinstance(B1, MemoryFile) else B1.read(1)

    orig_dtype = B0.dtype

    B0 = 10 * numpy.log(B0)
    B1 = 10 * numpy.log(B1)
    B2 = (B0 / B1)

    data = numpy.array([B0, B1, B2]).astype(orig_dtype)

    creation_args = next(iter(stack.values())).meta.copy()

    creation_args['count'] = 3

    # Open memory destination file.
    memfile = MemoryFile()
    dst = memfile.open(**creation_args)
    dst.write(data)
    if as_file:
        return memfile
    else:
        return dst
