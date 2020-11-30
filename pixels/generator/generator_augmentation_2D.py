from os import listdir, mkdir
from os.path import isdir, isfile, join

import numpy as np
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import Sequence, plot_model, to_categorical


def upscaling_sample(tile, factor):
    """
    Input is a 2D tile
    Upscale array to artificial super resolution.
    Simply copy the value factor number of times. (out_shape) = (in_shape) * factor
    """
    sizex = tile.shape[0] * factor
    sizey = tile.shape[1] * factor
    # Get data block for this offset. The numpy indexing order is (y, x).
    data = tile[0 : int(sizex), 0 : int(sizey)]
    # Expand data repeating values by the factor to get back to the original size.
    return data.repeat(factor, axis=0).repeat(factor, axis=1)


def img_flip(X, axis=None):
    X_f = np.flip(X, axis)
    return np.array(X_f)


def add_noise(image, ran=100):
    MIN = np.nanmin(image)
    MAX = np.nanmax(image)
    r = (MAX - MIN) / ran
    noise = r * np.random.sample((image.shape[0], image.shape[0]))

    return np.array(image + noise)


def change_bright(image, ran=1):
    return np.array(image * ran)


def augmentation(data_X, data_Y):
    timeseries_flip = []
    timeseries_flip0 = []
    timeseries_flip1 = []
    timeseries_noise = []
    timeseries_bright = []
    for time in data_X:
        bands_flip = []
        bands_flip0 = []
        bands_flip1 = []
        bands_noise = []
        bands_bright = []
        for band in time:
            bands_flip.append(img_flip(band))
            bands_flip0.append(img_flip(band, 0))
            bands_flip1.append(img_flip(band, 1))
            bands_noise.append(add_noise(band, ran=100))
            bands_bright.append(change_bright(band, ran=1))
        timeseries_flip.append(bands_flip)
        timeseries_flip0.append(bands_flip0)
        timeseries_flip1.append(bands_flip1)
        timeseries_noise.append(bands_noise)
        timeseries_bright.append(bands_bright)

    results = np.asarray(
        [
            [np.array(timeseries_flip), img_flip(data_Y)],
            [np.array(timeseries_flip0), img_flip(data_Y, 0)],
            [np.array(timeseries_flip1), img_flip(data_Y, 1)],
            [np.array(timeseries_noise), data_Y],
            [np.array(timeseries_bright), data_Y],
        ]
    )
    return results
    # Flip
    # Add noise
    # brightness_range # ran > 1  Brightness of Image increases


def generator_augmentation(data, num_time):

    results = augmentation(data["x_data"], data["y_data"])
    ori = np.array([data["x_data"], data["y_data"]])
    results = np.concatenate((results, [ori]), axis=0)
    for res in results:
        X = np.swapaxes(res[0], 1, 2)
        X = np.swapaxes(X, 2, 3)
        Y = np.expand_dims(res[1], axis=(0, -1))
        yield (np.array([X[:num_time]]), np.array([Y]))


def generator_2D(X, Y, mask, num_time=12, cloud_cover=0.7):
    # area = np.prod(mask.shape[1:])
    # cloud_sum = np.sum(mask, axis=(1, 2))
    # cloud_mask = np.ma.masked_where(cloud_sum >= area*cloud_cover, cloud_sum)
    # X = X[np.logical_not(cloud_mask.mask)]
    # Mute cloudy pixels.
    for i in range(X.shape[0]):
        X[i][:, mask[i]] = 0
    # Reshape X to have bands (features) last.
    X = np.swapaxes(X, 1, 2)
    X = np.swapaxes(X, 2, 3)
    # Increase dims to match the shape of the last layer's output tensor.
    Y = np.expand_dims(Y, axis=(0, -1))
    # Pad array wit zeros to ensure 12 time steps.
    if X.shape[0] < num_time:
        X = np.vstack((X, np.zeros((num_time - X.shape[0], *X.shape[1:]))))
    # Limit X to 12 time steps incase there are more.
    X = X[:num_time]
    # Return data.
    return np.array([X]), np.array([Y])