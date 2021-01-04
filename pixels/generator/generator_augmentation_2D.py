import numpy as np

AUGMENTATION_FACTOR = 3


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


def set_standard_shape(tensor, sizex=360, sizey=360):
    """
    Set input data from any shape to (*dims, sizex, sizey)
    """
    shp = tensor.shape
    size_tuple = (sizex, sizey)
    for i in range(len(shp)):
        curent_pair = shp[i : i + 2]
        if curent_pair == size_tuple:
            end = i + 2
    if end < len(shp):
        tensor = np.swapaxes(tensor, end - 1, end)
        tensor = np.swapaxes(tensor, end - 2, end - 1)
        tensor = set_standard_shape(tensor, sizex, sizey)
    return tensor


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


def augmentation(X, Y, sizex=360, sizey=360, augmentation_index=None):
    original_shape_X = X.shape
    original_shape_Y = Y.shape
    data_X = set_standard_shape(X, sizex=sizex, sizey=sizey)
    data_Y = np.squeeze(Y)
    data_X = np.squeeze(data_X)
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
            if augmentation_index is None or augmentation_index == 1:
                bands_flip.append(img_flip(band))
            if augmentation_index is None or augmentation_index == 2:
                bands_flip0.append(img_flip(band, 0))
            if augmentation_index is None or augmentation_index == 3:
                bands_flip1.append(img_flip(band, 1))
            if augmentation_index is None or augmentation_index == 4:
                bands_noise.append(add_noise(band, ran=10))
            if augmentation_index is None or augmentation_index == 5:
                bands_bright.append(change_bright(band, ran=10))
        timeseries_flip.append(bands_flip)
        timeseries_flip0.append(bands_flip0)
        timeseries_flip1.append(bands_flip1)
        timeseries_noise.append(bands_noise)
        timeseries_bright.append(bands_bright)

    if augmentation_index is None or augmentation_index == 1:
        timeseries_flip = np.array(timeseries_flip)
        timeseries_flip = np.swapaxes(
            timeseries_flip,
            len(timeseries_flip.shape) - 2,
            len(timeseries_flip.shape) - 3,
        )
        timeseries_flip = np.swapaxes(
            timeseries_flip,
            len(timeseries_flip.shape) - 1,
            len(timeseries_flip.shape) - 2,
        )
    if augmentation_index is None or augmentation_index == 2:
        timeseries_flip0 = np.array(timeseries_flip0)
        timeseries_flip0 = np.swapaxes(
            timeseries_flip0,
            len(timeseries_flip0.shape) - 2,
            len(timeseries_flip0.shape) - 3,
        )
        timeseries_flip0 = np.swapaxes(
            timeseries_flip0,
            len(timeseries_flip0.shape) - 1,
            len(timeseries_flip0.shape) - 2,
        )
    if augmentation_index is None or augmentation_index == 3:
        timeseries_flip1 = np.array(timeseries_flip1)
        timeseries_flip1 = np.swapaxes(
            timeseries_flip1,
            len(timeseries_flip1.shape) - 2,
            len(timeseries_flip1.shape) - 3,
        )
        timeseries_flip1 = np.swapaxes(
            timeseries_flip1,
            len(timeseries_flip1.shape) - 1,
            len(timeseries_flip1.shape) - 2,
        )
    if augmentation_index is None or augmentation_index == 4:
        timeseries_noise = np.array(timeseries_noise)
        timeseries_noise = np.swapaxes(
            timeseries_noise,
            len(timeseries_noise.shape) - 2,
            len(timeseries_noise.shape) - 3,
        )
        timeseries_noise = np.swapaxes(
            timeseries_noise,
            len(timeseries_noise.shape) - 1,
            len(timeseries_noise.shape) - 2,
        )
    if augmentation_index is None or augmentation_index == 5:
        timeseries_bright = np.array(timeseries_bright)
        timeseries_bright = np.swapaxes(
            timeseries_bright,
            len(timeseries_bright.shape) - 2,
            len(timeseries_bright.shape) - 3,
        )
        timeseries_bright = np.swapaxes(
            timeseries_bright,
            len(timeseries_bright.shape) - 1,
            len(timeseries_bright.shape) - 2,
        )

    if augmentation_index == 0:
        return (
            X,
            np.array([data_Y]).reshape(original_shape_Y),
        )
    elif augmentation_index == 1:
        return (
            np.array(timeseries_flip).reshape(original_shape_X),
            np.array([img_flip(data_Y)]).reshape(original_shape_Y),
        )
    elif augmentation_index == 2:
        return (
            np.array(timeseries_flip0).reshape(original_shape_X),
            np.array([img_flip(data_Y, 0)]).reshape(original_shape_Y),
        )
    elif augmentation_index == 3:
        return (
            np.array(timeseries_flip1).reshape(original_shape_X),
            np.array([img_flip(data_Y, 1)]).reshape(original_shape_Y),
        )
    elif augmentation_index == 4:
        return (
            np.array(timeseries_noise).reshape(original_shape_X),
            np.array([data_Y]).reshape(original_shape_Y),
        )
    elif augmentation_index == 5:
        return (
            np.array(timeseries_bright).reshape(original_shape_X),
            np.array([data_Y]).reshape(original_shape_Y),
        )

    results_x = np.asarray(
        [
            np.array(timeseries_flip).reshape(original_shape_X),
            # np.array(timeseries_flip),
            np.array(timeseries_flip0).reshape(original_shape_X),
            np.array(timeseries_flip1).reshape(original_shape_X),
            np.array(timeseries_noise).reshape(original_shape_X),
            np.array(timeseries_bright).reshape(original_shape_X),
            X,
        ]
    )
    results_y = np.asarray(
        [
            np.array([img_flip(data_Y)]).reshape(original_shape_Y),
            np.array([img_flip(data_Y, 0)]).reshape(original_shape_Y),
            np.array([img_flip(data_Y, 1)]).reshape(original_shape_Y),
            np.array([data_Y]).reshape(original_shape_Y),
            np.array([data_Y]).reshape(original_shape_Y),
            np.array([data_Y]).reshape(original_shape_Y),
        ]
    )

    return (
        results_x.reshape(np.prod(results_x.shape[:2]), *results_x.shape[2:]),
        results_y.reshape(np.prod(results_y.shape[:2]), *results_y.shape[2:]),
    )
    # Flip
    # Add noise
    # brightness_range # ran > 1  Brightness of Image increases


def generator_2D(X, Y, mask, num_time=12, cloud_cover=0.7):
    area = np.prod(mask.shape[1:])
    cloud_sum = np.sum(mask, axis=(1, 2))
    if num_time>len(cloud_sum):
        num_time = len(cloud_sum)
    ind = np.sort(np.argpartition(cloud_sum,num_time)[:num_time])
    X = X[ind]
    # cloud_mask = np.ma.masked_where(cloud_sum >= area*cloud_cover, cloud_sum)
    # X = X[np.logical_not(cloud_mask.mask)]
    # Mute cloudy pixels.
    # for i in range(X.shape[0]):
    #    X[i][:, mask[i]] = 0
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


def generator_single_2D(X, Y, mask, num_time=12, cloud_cover=0.7):
    area = np.prod(mask.shape[1:])
    cloud_sum = np.sum(mask, axis=(1, 2))
    cloud_mask = np.ma.masked_where(cloud_sum >= area * cloud_cover, cloud_sum)
    X = X[np.logical_not(cloud_mask.mask)]
    # Mute cloudy pixels.
    # for i in range(X.shape[0]):
    #    X[i][:, mask[i]] = 0
    # Reshape X to have bands (features) last.
    X = np.swapaxes(X, 1, 2)
    X = np.swapaxes(X, 2, 3)
    # Increase dims to match the shape of the last layer's output tensor.
    Y = np.expand_dims(Y, axis=(0, -1))
    # Y = [Y]
    Y_aux = Y
    for i in range(len(X) - 1):
        Y_aux = np.append(Y_aux, Y, axis=0)
    Y = Y_aux
    # Pad array wit zeros to ensure 12 time steps.
    # if X.shape[0] < num_time:
    #    X = np.vstack((X, np.zeros((num_time - X.shape[0], *X.shape[1:]))))
    # Limit X to 12 time steps incase there are more.
    # X = X[:num_time]
    # Return data.
    return np.array(X), np.array(Y)
