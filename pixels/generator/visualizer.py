import math

import matplotlib.pyplot as plt
import numpy as np
import sentry_sdk
from matplotlib import cm
from PIL import Image


def visualize_in_item(X, Y, prediction=False, in_out="IN", RGB=None, scaling=1000):
    if RGB is None:
        RGB = [8, 7, 6]
    num_Y = len(Y)
    dat = np.squeeze(Y)
    if len(X.shape) > 4:
        count = (2 * num_Y) + np.prod(X.shape[:2])
    else:
        count = (2 * num_Y) + len(X)
    if in_out == "OUT":
        dat = Y[0]
        dat = np.squeeze(dat)
        img_c = dat.shape[0]
        # If the second dimension is an image size do not squeeze.
        # Prevent squeezing on single image inputs. (N, 360, 360, bands), prevents failing if N==1
        if np.array(X).shape[1] != img_c:
            X = X.reshape(np.prod(X.shape[:2]), *X.shape[2:])
    # Export Y and RGB as images.
    # Count number of items for the combined image, adding +2 for Y and Composite viz.
    # count = 2 + len(X)
    width = math.ceil(math.sqrt(count))
    height = math.ceil(math.sqrt(count))
    padding = 5
    img_c = dat.shape[0]
    img_l = dat.shape[1]
    # TODO: Change this for multiple predictions, to use only with single square mode
    if np.any(prediction):
        if len(np.squeeze(prediction).shape) > 2:
            count = (2 * len(X)) + 2
            width = math.ceil(math.sqrt(count))
            height = math.ceil(math.sqrt(count))

    # Construct target array for image.
    target = np.zeros(
        (
            img_c * height + padding * (height - 1),
            img_l * width + padding * (width - 1),
            3,
        )
    ).astype("uint8")
    # Get data for Y.
    # Greyscale -> grey_max/min limit values to clip
    # grey_max = 10
    # grey_min = 0
    ydata = cm.viridis_r(np.squeeze(dat))
    ydata = np.ceil((255 * ydata)).astype("uint8")
    # ydata = np.ceil((255 * np.clip(dat, grey_min, grey_max) / grey_max))#.astype('uint8')
    # ydata = (255 * np.clip(dat, grey_min, grey_max) / grey_max)#.astype('uint8')
    ydata[ydata == 0] = 255
    ydata = ydata[:img_c, :img_l]
    target[:img_c, :img_l, 0] = ydata[:, :, 0]
    target[:img_c, :img_l, 1] = ydata[:, :, 1]
    target[:img_c, :img_l, 2] = ydata[:, :, 2]
    for i in range(num_Y):
        ydata = cm.viridis_r(np.squeeze(Y[i]))
        ydata = np.ceil((255 * ydata)).astype("uint8")
        ydata[ydata == 0] = 255
        ydata = ydata[:img_c, :img_l]
        xoffset = (i) % width
        yoffset = math.floor((i) / width)
        initial_y = yoffset * img_l + yoffset * padding
        final_y = (yoffset + 1) * img_c + yoffset * padding

        initial_x = xoffset * img_c + xoffset * padding
        final_x = (xoffset + 1) * img_l + xoffset * padding

        try:
            target[initial_y:final_y, initial_x:final_x, :] = ydata[:, :, :3]
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print("Failed")
            raise

    if np.any(prediction):
        if len(np.squeeze(prediction).shape) <= 2:
            # Get data for prediction.
            preddata = cm.viridis_r(np.squeeze(prediction))
            preddata = np.ceil((255 * preddata)).astype("uint8")
            # preddata = np.ceil((255 * np.clip(np.squeeze(preddata), grey_min, grey_max) / grey_max)).astype('uint8')
            preddata[preddata == 0] = 255
            preddata = preddata[:img_c, :img_l]
            # preddata = cm.viridis_r(preddata)
            target[:img_c, (img_l + padding) : ((img_c * 2) + padding), 0] = preddata[
                :, :, 0
            ]
            target[:img_c, (img_l + padding) : ((img_c * 2) + padding), 1] = preddata[
                :, :, 1
            ]
            target[:img_c, (img_l + padding) : ((img_c * 2) + padding), 2] = preddata[
                :, :, 2
            ]
        else:
            for i in range(len(prediction)):
                preddata = cm.viridis_r(np.squeeze(prediction[i]))
                preddata = np.ceil((255 * preddata)).astype("uint8")
                preddata[preddata == 0] = 255
                preddata = preddata[:img_c, :img_l]
                xoffset = (i + 2 + len(X)) % width
                yoffset = math.floor((i + 2 + len(X)) / width)
                try:
                    target[
                        (yoffset * img_c + yoffset * padding) : (
                            (yoffset + 1) * img_l + yoffset * padding
                        ),
                        (xoffset * img_c + xoffset * padding) : (
                            (xoffset + 1) * img_l + xoffset * padding
                        ),
                    ] = preddata[:, :, :3]
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    print("Failed")
                    raise

    # Compute composite.
    for i in range(len(X)):
        if in_out == "IN":
            rgb = np.dstack(
                [
                    255 * (np.clip(X[i][RGB[0], :, :], 0, scaling) / scaling),
                    255 * (np.clip(X[i][RGB[1], :, :], 0, scaling) / scaling),
                    255 * (np.clip(X[i][RGB[2], :, :], 0, scaling) / scaling),
                ]
            ).astype("uint8")
        if in_out == "OUT":
            rgb = np.dstack(
                [
                    255 * (np.clip(X[i][:, :, RGB[0]], 0, scaling) / scaling),
                    255 * (np.clip(X[i][:, :, RGB[1]], 0, scaling) / scaling),
                    255 * (np.clip(X[i][:, :, RGB[2]], 0, scaling) / scaling),
                ]
            ).astype("uint8")

        # Compute offset for this date (adding 2 to account for the Y slot, and for the Composite).
        xoffset = (i + num_Y + 1) % width
        yoffset = math.floor((i + num_Y + 1) / width)
        try:
            target[
                (yoffset * img_c + yoffset * padding) : (
                    (yoffset + 1) * img_c + yoffset * padding
                ),
                (xoffset * img_l + xoffset * padding) : (
                    (xoffset + 1) * img_l + xoffset * padding
                ),
            ] = rgb
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print("Failed")
            raise
    img = Image.fromarray(target)
    plt.figure(figsize=(15, 15))
    plt.imshow(img)
    plt.show()
    return img
