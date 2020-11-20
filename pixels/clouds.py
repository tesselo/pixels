import numpy

SCALE = 10000


def composite_index(B02, B03, B04, B08, B8A, B11, B12):
    """
    Shortcut for composite index.
    """
    return _composite_or_cloud(B02, B03, B04, B08, B8A, B11, B12, cloud_only=False)


def cloud_or_snow_mask(B02, B03, B04, B08, B8A, B11, B12):
    """
    Shortcut for cloud mask.
    """
    return _composite_or_cloud(B02, B03, B04, B08, B8A, B11, B12, cloud_only=True)


def _composite_or_cloud(B02in, B03in, B04in, B08in, B8Ain, B11in, B12in, cloud_only=True, light_clouds=False):
    """
    Compute cloud and snow mask or create a composite.

    Input should be 3D tensors should be (time, height, width)

    Refs:
    https://usermanual.readthedocs.io/en/latest/pages/References.html#s2gmatbd
    https://usermanual.readthedocs.io/en/latest/_downloads/76c99b523c9067757b4b81a022345086/S2GM-SC2-ATBD-BC-v1.3.2.pdf
    """
    # Nodata mask.
    NODATA_VALUE = 0
    nodata_mask = B02in == NODATA_VALUE

    # Rescale images.
    B02 = numpy.clip(B02in, 0, SCALE) / SCALE
    B03 = numpy.clip(B03in, 0, SCALE) / SCALE
    B04 = numpy.clip(B04in, 0, SCALE) / SCALE
    B08 = numpy.clip(B08in, 0, SCALE) / SCALE
    B8A = numpy.clip(B8Ain, 0, SCALE) / SCALE
    B11 = numpy.clip(B11in, 0, SCALE) / SCALE
    B12 = numpy.clip(B12in, 0, SCALE) / SCALE

    # Prep vars.
    ratioB3B11 = B03 / B11
    ratioB11B3 = B11 / B03
    rgbMean = (B02 + B03 + B04) / 3
    tcHaze = -0.8239 * B02 + 0.0849 * B03 + 0.4396 * B04 - 0.058 * B8A + 0.2013 * B11 - 0.2773 * B12
    normDiffB8B11 = (B08 - B11) / (B08 + B11)
    tcb = 0.3029 * B02 + 0.2786 * B03 + 0.4733 * B04 + 0.5599 * B8A + 0.508 * B11 + 0.1872 * B12
    ndwi = (B03 - B11) / (B03 + B11)

    # Snow.
    isSnow = (ndwi > 0.7) & numpy.logical_not((ratioB3B11 > 1) & (tcb < 0.36))

    # Dense clouds.
    A = (((ratioB3B11 > 1) & (rgbMean > 0.3)) & ((tcHaze < -0.1) | ((tcHaze > -0.08) & (normDiffB8B11 < 0.4))))
    B = (tcHaze < -0.2)
    C = ((ratioB3B11 > 1) & (rgbMean < 0.3))
    D = ((tcHaze < -0.055) & (rgbMean > 0.12))
    E = (numpy.logical_not((ratioB3B11 > 1) & (rgbMean < 0.3)) & ((tcHaze < -0.09) & (rgbMean > 0.12)))
    isHighProbCloud = A | B | C & D | E

    # Compute cloud mask.
    # cloud_mask = isSnow | isHighProbCloud | isLowProbCloud | nodata_mask
    cloud_mask = isSnow | isHighProbCloud | nodata_mask

    # Light clouds.
    if light_clouds:
        A = (((ratioB11B3 > 1) & (rgbMean < 0.2)) & ((tcHaze < -0.1) | ((tcHaze < -0.08) & (normDiffB8B11 < 0.4))))
        C = ((ratioB3B11 > 1) & (rgbMean < 0.2))
        E = (numpy.logical_not((ratioB3B11 > 1) & (rgbMean < 0.2)) & ((tcHaze < -0.02) & (rgbMean > 0.12)))
        isLowProbCloud = A | B | C & D | E
        cloud_mask = cloud_mask | isLowProbCloud

    # Return early for cloud mask mode.
    if cloud_only:
        return cloud_mask

    # Prepare abstract selector index.
    idx1, idx2 = numpy.indices(cloud_mask.shape[1:])

    # Prepare additional indices for composite section.
    ndvi = (B08 - B04) / (B08 + B04)

    # For composites, reduce the data to valid observations.
    ndvi[cloud_mask] = numpy.nan
    ndwi[cloud_mask] = numpy.nan
    tcb[cloud_mask] = numpy.nan

    # Compute averages and min/max indexes.
    ndwiMean = numpy.nanmean(ndwi, axis=0)
    ndwiMin = numpy.nanmin(ndwi, axis=0)
    ndwi_allnan_slice_save = numpy.copy(ndwi)  # Avoid nanargmax All-NaN slice error.
    ndwi_allnan_slice_save[0, numpy.isnan(ndwiMean)] = 0
    ndwiMaxIndex = numpy.nanargmax(ndwi_allnan_slice_save, axis=0)

    ndviMean = numpy.nanmean(ndvi, axis=0)
    ndviMax = numpy.nanmax(ndvi, axis=0)
    ndvi_allnan_slice_save = numpy.copy(ndvi)  # Avoid nanargmax All-NaN slice error.
    ndvi_allnan_slice_save[0, numpy.isnan(ndviMean)] = 0
    ndviMinIndex = numpy.nanargmin(ndvi_allnan_slice_save, axis=0)
    ndviMaxIndex = numpy.nanargmax(ndvi_allnan_slice_save, axis=0)

    tcbMean = numpy.nanmean(tcb, axis=0)
    tcb_allnan_slice_save = numpy.copy(tcb)  # Avoid nanargmax All-NaN slice error.
    tcb_allnan_slice_save[0, numpy.isnan(tcbMean)] = 0
    tcbMinIndex = numpy.nanargmin(tcb_allnan_slice_save, axis=0)

    # Prepare result array.
    result = -numpy.ones(ndvi.shape[1:])

    # Criteria 1
    # if mndwiMean < -0.55 & ndvi[ndviMaxIndex] - ndviMean < 0.05:
    #     index = ndviMaxIndex
    # selector = (ndwiMean < -0.55) & ((ndvi[ndviMaxIndex, idx1, idx2] - ndviMean) < 0.05)
    selector = (ndwiMean < -0.55) & ((ndviMax - ndviMean) < 0.05)
    result[selector] = ndviMaxIndex[selector]
    # print('R1', numpy.sum(result==-1))

    # Criteria 2
    # elif (ndviMean < -0.3 & mndwiMean -mndwi[mndwiMinIndex] < 0.05):
    #     index = mndwiMaxIndex
    # selector = (ndviMean < -0.3) & ((ndwiMean - ndwi[ndwiMinIndex, idx1, idx2]) < 0.05)
    selector = (ndviMean < -0.3) & ((ndwiMean - ndwiMin) < 0.05)
    selector = selector & (result == -1)
    result[selector] = ndwiMaxIndex[selector]
    # print('R2', numpy.sum(result==-1))

    # Criteria 3
    # elif (ndviMean > 0.6 & tcbMean < 0.45):
    #     index = ndviMaxIndex
    selector = (ndviMean > 0.6) & (tcbMean < 0.45)
    selector = selector & (result == -1)
    result[selector] = ndviMaxIndex[selector]
    # print('R3', numpy.sum(result==-1))

    # Criteria 4
    # elif (numpy.logical_not(cloudTest[tcbMinIndex])):
    #     index = tcbMinIndex
    selector = numpy.logical_not(isHighProbCloud[tcbMinIndex, idx1, idx2])
    selector = selector & (result == -1)
    result[selector] = tcbMinIndex[selector]
    # print('R4', numpy.sum(result==-1))

    # Criteria 5
    # elif (numpy.logical_not(snowTest[tcbMinIndex])):
    #     if (tcb[tcbMinIndex] > 1.0):
    #         index = undefined
    #     else:
    #         index = tcbMinIndex
    selector = numpy.logical_not(isSnow[tcbMinIndex, idx1, idx2]) & (tcb[tcbMinIndex, idx1, idx2] < 1)
    selector = selector & (result == -1)
    result[selector] = tcbMinIndex[selector]
    # print('R5', numpy.sum(result==-1))

    # Criteria 6
    # elif (ndviMean < -0.2):
    #     index = mndwiMaxIndex
    selector = ndviMean < -0.2
    selector = selector & (result == -1)
    result[selector] = ndwiMaxIndex[selector]
    # print('R6', numpy.sum(result==-1))

    # Criteria 7
    # elif (tcbMean > 0.45):
    #     index = ndviMinIndex
    selector = tcbMean > 0.45
    selector = selector & (result == -1)
    result[selector] = ndviMinIndex[selector]
    # print('R7', numpy.sum(result==-1))

    # Criteria 8
    # else:
    #     index = ndviMaxIndex
    selector = result == -1
    result[selector] = ndviMaxIndex[selector]

    return result.astype('uint8')
