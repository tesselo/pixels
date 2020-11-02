
# TCB= 0.3029·B02 + 0.2786·B03 + 0.4733·B04 + 0.5599·B8A + 0.508·B11 + 0.1872·B12
# NDSI = (B03 -B11) / (B03 + B11)
# function isSnow(sample) {

#    let scl_snow = sample.SCL === 11

#
#    let tcb= computeTCB(sample)

#
#     let ndsi = computeNdsi(sample)

#
#     let s2gm_snow = ndsi > 0.6 and tcb> 0.36

#
#     return scl_snow and s2gm_snow

#
# }

import numpy


def cloud_or_snow(B02in, B03in, B04in, B08in, B8Ain, B11in, B12in, include_low=True):
    """
    Compute cloud and snow mask.

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

    # Snow.
    isSnow = (((B03 - B11) / (B03 + B11)) > 0.7) & numpy.logical_not((ratioB3B11 > 1) & ((0.3029 * B02 + 0.2786 * B03 + 0.4733 * B04 + 0.5599 * B08 + 0.508 * B11 + 0.1872 * B12) < 0.36))

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

    return isSnow | isHighProbCloud | isLowProbCloud


# def choose():
    # ndvi = (B08 - B04) / (B08 + B04)
    # ndwi = (B03 - B11) / (B03 + B11)
    # tcb = 0.3029 * B02 + 0.2786 * B03 + 0.4733 * B04 + 0.5599 * B8A + 0.508 * B11 + 0.1872 * B12
    # brightness = B02 + B03 + B04
    # meanB11B12 = (B11 + B12) / 2

    # one valid observation
    # return that observation

    # # two and three valid observations
    # if mndwiMean < -0.55 & ndvi[ndviMaxIndex] -ndviMean < 0.05:
    #     index = ndviMaxIndex
    # elif (ndviMean < -0.3 & mndwiMean -mndwi[mndwiMinIndex] < 0.05):
    #     index = mndwiMaxIndex
    # elif (ndviMean > 0.6 & tcbMean < 0.45):
    #     index = ndviMaxIndex
    # elif (!cloudTest[tcbMinIndex]):
    #     index = tcbMinIndex
    # elif (!snowTest[tcbMinIndex]):
    #     if (tcb[tcbMinIndex] > 1.0):
    #         index = undefined
    #     else:
    #         index = tcbMinIndex
    # elif (ndviMean < -0.2):
    #     index = mndwiMaxIndex
    # elif (tcbMean > 0.45):.
    #     index = ndviMinIndex
    # else:
    #     index = ndviMaxIndex
