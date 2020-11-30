import math

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def visualize_in_item(X, Y, prediction=False, in_out="IN"):
    dat = Y
    if in_out == "OUT":
        dat = np.squeeze(Y)
        X = np.squeeze(X)
    # Export Y and RGB as images.
    # Count number of items for the combined image, adding +2 for Y and Composite viz.
    count = 2 + len(X)
    width = math.ceil(math.sqrt(count))
    height = math.ceil(math.sqrt(count))
    padding = 5
    img_c = dat.shape[0]
    img_l = dat.shape[1]
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
    grey_max = 10
    grey_min = 0
    ydata = cm.viridis_r(np.squeeze(dat))
    ydata = np.ceil((255 * ydata)).astype("uint8")
    # ydata = np.ceil((255 * np.clip(dat, grey_min, grey_max) / grey_max))#.astype('uint8')
    # ydata = (255 * np.clip(dat, grey_min, grey_max) / grey_max)#.astype('uint8')
    ydata[ydata == 0] = 255
    ydata = ydata[:img_c, :img_l]
    target[:img_c, :img_l, 0] = ydata[:, :, 0]
    target[:img_c, :img_l, 1] = ydata[:, :, 1]
    target[:img_c, :img_l, 2] = ydata[:, :, 2]

    if np.any(prediction):
        # Get data for prediction.
        preddata = cm.viridis_r(np.squeeze(prediction))
        preddata = np.ceil((255 * preddata)).astype("uint8")
        # preddata = np.ceil((255 * np.clip(np.squeeze(preddata), grey_min, grey_max) / grey_max)).astype('uint8')
        preddata[preddata == 0] = 255
        preddata = preddata[:img_c, :img_l]
        # preddata = cm.viridis_r(preddata)
        # print(preddata[:,:,0])
        target[:img_c, (img_l + padding) : ((img_c * 2) + padding), 0] = preddata[
            :, :, 0
        ]
        target[:img_c, (img_l + padding) : ((img_c * 2) + padding), 1] = preddata[
            :, :, 1
        ]
        target[:img_c, (img_l + padding) : ((img_c * 2) + padding), 2] = preddata[
            :, :, 2
        ]
    # Compute composite.
    # X = src['x_data']
    # cidx  = composite_index(X[:, 8], X[:, 7], X[:, 6], X[:, 2], X[:, 1], X[:, 0], X[:, 9])
    # idx1, idx2 = np.indices(X.shape[2:])
    # composite = X[cidx, :, idx1, idx2]
    # rgb = np.dstack([
    #   255 * (np.clip(composite[:256, :256, 8], 0, 1000) / 1000),
    #   255 * (np.clip(composite[:256, :256, 7], 0, 1000) / 1000),
    #   255 * (np.clip(composite[:256, :256, 6], 0, 1000) / 1000),
    # ]).astype('uint8')
    # target[:256, (256 + padding):(512 + padding), :] = rgb

    for i in range(len(X)):
        # date = src['dates'][i][0]['properties']['datetime'][:10]
        # print(date)
        if in_out == "IN":
            rgb = np.dstack(
                [
                    255 * (np.clip(X[i][8, :, :], 0, 1000) / 1000),
                    255 * (np.clip(X[i][7, :, :], 0, 1000) / 1000),
                    255 * (np.clip(X[i][6, :, :], 0, 1000) / 1000),
                ]
            ).astype("uint8")
        if in_out == "OUT":
            rgb = np.dstack(
                [
                    255 * (np.clip(X[i][:, :, 8], 0, 1000) / 1000),
                    255 * (np.clip(X[i][:, :, 7], 0, 1000) / 1000),
                    255 * (np.clip(X[i][:, :, 6], 0, 1000) / 1000),
                ]
            ).astype("uint8")

        # Compute offset for this date (adding 2 to account for the Y slot, and for the Composite).
        xoffset = (i + 2) % width
        yoffset = math.floor((i + 2) / width)

        try:
            target[
                (yoffset * img_c + yoffset * padding) : (
                    (yoffset + 1) * img_l + yoffset * padding
                ),
                (xoffset * img_c + xoffset * padding) : (
                    (xoffset + 1) * img_l + xoffset * padding
                ),
            ] = rgb
        except:
            print("Failed")
            raise

    img = Image.fromarray(target)
    plt.figure(figsize=(15, 15))
    plt.imshow(img)
    plt.show()
    return img