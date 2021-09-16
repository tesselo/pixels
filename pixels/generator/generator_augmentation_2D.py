import numpy as np

AUGMENTATION_FACTOR = 4


def upscaling_sample(tile, factor):
    """
    Input is a 2D tile
    Upscale array to artificial super resolution.
    Simply copy the value factor number of times. (out_shape) = (in_shape) * factor
    """
    sizex = tile.shape[0] * factor
    sizey = tile.shape[1] * factor
    if not isinstance(factor, int):
        import scipy

        return scipy.ndimage.zoom(tile, zoom=(factor), order=1)
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


def upscale_multiple_images(images_array, upscale_factor=10):
    """
    Upscale multiple images.

    TODO: Decide if format is closed or open, if there is 2 loops or possible more.

    Parameters
    ----------
        images_array : numpy array
            List of images (Timestep, bands, img).
        upscale_factor : int

    Returns
    -------
        images_up : numpy array
            List of images upscale by upscale_factor (Timestep, bands, img*upscale_factor).
    """
    new_array = []
    for time in images_array:
        new_time = []
        for bands in time:
            new_img = upscaling_sample(bands, upscale_factor)
            new_time.append(np.array(new_img))
        new_array.append(np.array(new_time))
    return np.array(new_array)


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

def select_augmentation(img, augmentation_index):
    if augmentation_index is None or augmentation_index == 1:
        return img_flip(img)
    if augmentation_index is None or augmentation_index == 2:
        return img_flip(img, 0)
    if augmentation_index is None or augmentation_index == 3:
        return img_flip(img, 1)
    if augmentation_index is None or augmentation_index == 4:
        return add_noise(img, ran=10)
    if augmentation_index is None or augmentation_index == 5:
        return change_bright(img, ran=10)

def augmentation_loops(imgs, augmentation_index):
    # Do the augmentations on images (N, B, height, width).
    time_aug_imgs = []
    for N in imgs:
        aug_img = []
        for B in N:
            aug_img.append(select_augmentation(B, augmentation_index))
        time_aug_imgs.append(aug_img)
    # Revert shapes back to (N, height, width, B)
    time_aug_imgs = np.array(time_aug_imgs)
    time_aug_imgs = np.swapaxes(
        time_aug_imgs,
        len(time_aug_imgs.shape) - 2,
        len(time_aug_imgs.shape) - 3,
    )
    time_aug_imgs = np.swapaxes(
        time_aug_imgs,
        len(time_aug_imgs.shape) - 1,
        len(time_aug_imgs.shape) - 2,
    )
    return np.array(time_aug_imgs)

def augmentation(X, Y, sizex=360, sizey=360, augmentation_index=None):
    data_X = set_standard_shape(X, sizex=sizex, sizey=sizey)
    data_Y = set_standard_shape(Y, sizex=sizex, sizey=sizey)
    data_Y = np.squeeze(data_Y)
    data_X = np.squeeze(data_X)
    if len(data_X.shape) < 4:
        data_X = np.expand_dims(data_X, list(np.arange(4-len(data_X.shape))))
    if len(data_Y.shape) < 4:
        data_Y = np.expand_dims(data_Y, list(np.arange(4-len(data_Y.shape))))
    resulted_augmentation_X = [X[0]]
    resulted_augmentation_Y = [Y]
    for i in augmentation_index:
        # i has to be +1 because the 1st augmentation is 1.
        resulted_augmentation_X.append(augmentation_loops(data_X, i))
        resulted_augmentation_Y.append(augmentation_loops(data_Y, i))
    resulted_augmentation_X = np.array([np.array(img) for img in resulted_augmentation_X])
    resulted_augmentation_Y = np.array([np.array(img) for img in resulted_augmentation_Y])
    resulted_augmentation_Y = np.squeeze(resulted_augmentation_Y)
    return (
        resulted_augmentation_X,
        resulted_augmentation_Y,
    )
    # Flip
    # Add noise
    # brightness_range # ran > 1  Brightness of Image increases


def generator_2D(X, Y, mask, num_time=12, cloud_cover=0.7, prediction_mode=False):
    # For prediction from uncleaned data, keep the least cloudy dates.
    if prediction_mode:
        # Compute number of cloudy pixels per date.
        cloud_sum = np.sum(mask, axis=(1, 2))
        # Create an index of the least cloudy dates, with a maximum of
        # "num_time" dates.
        ind = np.sort(np.argpartition(cloud_sum, len(cloud_sum) - 1)[:num_time])
        # Reduce to the best dates.
        X = X[ind]
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
