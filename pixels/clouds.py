import numpy


def cloud_or_snow(B02in, B03in, B04in, B08in, B8Ain, B11in, B12in, composite=True):
    """
    Compute cloud and snow mask.

    Input should be 3D tensors should be (time, height, width)

    Refs:
    https://usermanual.readthedocs.io/en/latest/pages/References.html#s2gmatbd
    https://usermanual.readthedocs.io/en/latest/_downloads/76c99b523c9067757b4b81a022345086/S2GM-SC2-ATBD-BC-v1.3.2.pdf
    """
    # Rescale images.
    SCALE = 10000
    B02 = B02in / SCALE
    B03 = B03in / SCALE
    B04 = B04in / SCALE
    B08 = B08in / SCALE
    B8A = B8Ain / SCALE
    B11 = B11in / SCALE
    B12 = B12in / SCALE

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
    # isHighProbCloud = ((((ratioB3B11 > 1) & (rgbMean > 0.3)) & ((tcHaze < -0.1) | ((tcHaze > -0.08) & (normDiffB8B11 < 0.4)))) | (tcHaze < -0.2) | ((ratioB3B11 > 1) & (rgbMean < 0.3)) & ((tcHaze < -0.055) & (rgbMean > 0.12)) | (numpy.logical_not((ratioB3B11 > 1) & (rgbMean < 0.3)) & ((tcHaze< -0.09) & (rgbMean > 0.12))))
    A = (((ratioB3B11 > 1) & (rgbMean > 0.3)) & ((tcHaze < -0.1) | ((tcHaze > -0.08) & (normDiffB8B11 < 0.4))))
    B = (tcHaze < -0.2)
    C = ((ratioB3B11 > 1) & (rgbMean < 0.3))
    D = ((tcHaze < -0.055) & (rgbMean > 0.12))
    E = (numpy.logical_not((ratioB3B11 > 1) & (rgbMean < 0.3)) & ((tcHaze< -0.09) & (rgbMean > 0.12)))
    isHighProbCloud = A | B | C & D | E

    # Light clouds.
    A = (((ratioB11B3 > 1) & (rgbMean < 0.2)) & ((tcHaze < -0.1) | ((tcHaze < -0.08) & (normDiffB8B11 < 0.4))))
    C = ((ratioB3B11 > 1) & (rgbMean < 0.2))
    E = (numpy.logical_not((ratioB3B11 > 1) & (rgbMean < 0.2)) & ((tcHaze< -0.02) & (rgbMean > 0.12)))
    isLowProbCloud = A | B | C & D | E

    # Compute cloud mask.
    cloud_mask = isSnow | isHighProbCloud | isLowProbCloud

    # Composite section.
    ndvi = (B08 - B04) / (B08 + B04)
    brightness = B02 + B03 + B04
    meanB11B12 = (B11 + B12) / 2


    if composite:
        # Get all pixels that have only one valid observation.
        valid_input_counts = numpy.sum(numpy.logical_not(cloud_mask), axis=0)

        ndwiMean = numpy.mean(ndwi, axis=0)
        ndwiMaxIndex = numpy.argmax(ndwi, axis=0)
        ndviMean = numpy.mean(ndvi, axis=0)
        ndviMaxIndex = numpy.argmax(ndvi, axis=0)
        tcbMean = numpy.mean(tcb, axis=0)
        tcbMinIndex = numpy.argmin(tcb, axis=0)


        idx1, idx2 = numpy.indices(ndvi.shape[1:])
        composite_data = bnds[ndviMaxIndex, idx1, idx2]

        # two and three valid observations
        selector_index = (ndwiMean < -0.55) & ((ndvi[ndviMaxIndex] - ndviMean) < 0.05)

        import ipdb; ipdb.set_trace()
        if mndwiMean < -0.55 & ndvi[ndviMaxIndex] - ndviMean < 0.05:
            index = ndviMaxIndex
        elif (ndviMean < -0.3 & mndwiMean -mndwi[mndwiMinIndex] < 0.05):
            index = mndwiMaxIndex
        elif (ndviMean > 0.6 & tcbMean < 0.45):
            index = ndviMaxIndex
        elif (numpy.logical_not(cloudTest[tcbMinIndex])):
            index = tcbMinIndex
        elif (numpy.logical_not(snowTest[tcbMinIndex])):
            if (tcb[tcbMinIndex] > 1.0):
                index = undefined
            else:
                index = tcbMinIndex
        elif (ndviMean < -0.2):
            index = mndwiMaxIndex
        elif (tcbMean > 0.45):
            index = ndviMinIndex
        else:
            index = ndviMaxIndex

    else:
        return cloud_mask


def choose(X):
    """
    Input should be a 3D tensor with (scenes, timesteps, bands).
    """
    pass
#     ndvi = (B08 - B04) / (B08 + B04)
#     brightness = B02 + B03 + B04
#     meanB11B12 = (B11 + B12) / 2
#
#     # one valid observation
#     # return that observation
#
#     # two and three valid observations
#     if mndwiMean < -0.55 & ndvi[ndviMaxIndex] -ndviMean < 0.05:
#         index = ndviMaxIndex
#     elif (ndviMean < -0.3 & mndwiMean -mndwi[mndwiMinIndex] < 0.05):
#         index = mndwiMaxIndex
#     elif (ndviMean > 0.6 & tcbMean < 0.45):
#         index = ndviMaxIndex
#     elif (!cloudTest[tcbMinIndex]):
#         index = tcbMinIndex
#     elif (!snowTest[tcbMinIndex]):
#         if (tcb[tcbMinIndex] > 1.0):
#             index = undefined
#         else:
#             index = tcbMinIndex
#     elif (ndviMean < -0.2):
#         index = mndwiMaxIndex
#     elif (tcbMean > 0.45):.
#         index = ndviMinIndex
#     else:
#         index = ndviMaxIndex
