import numpy as np

AUGMENTATION_FACTOR = 4


def upscaling_sample(tile, factor):
    """
    Input is a 2D tile
    Upscale array to artificial super resolution.
    Simply copy the value factor number of times. (out_shape) = (in_shape) * factor
    """
    x_size = tile.shape[0] * factor
    y_size = tile.shape[1] * factor
    if not isinstance(factor, int):
        import scipy

        return scipy.ndimage.zoom(tile, zoom=(factor), order=1)
    # Get data block for this offset. The numpy indexing order is (y, x).
    data = tile[0 : int(x_size), 0 : int(y_size)]
    # Expand data repeating values by the factor to get back to the original size.
    return data.repeat(factor, axis=0).repeat(factor, axis=1)


def set_standard_shape(tensor, x_size=360, y_size=360):
    """
    Set input data from any shape to (*dims, sizex, sizey)
    """
    shape = tensor.shape
    size_tuple = (x_size, y_size)
    shape_len = len(shape)
    end = 0
    for i in range(shape_len):
        current_pair = shape[i : i + 2]
        if current_pair == size_tuple:
            end = i + 2
    if end < shape_len:
        tensor = np.swapaxes(tensor, end - 1, end)
        tensor = np.swapaxes(tensor, end - 2, end - 1)
        tensor = set_standard_shape(tensor, x_size, y_size)
    return tensor


def upscale_images(images, upscale_factor=10):
    """
    Upscale multiple images.

    TODO: Decide if format is closed or open, if there is 2 loops or possible more.

    Parameters
    ----------
        images : numpy array
            List of images (Timestep, bands, img).
        upscale_factor : int

    Returns
    -------
        images_up : numpy array
            List of images upscale by upscale_factor (Timestep, bands, img*upscale_factor).
    """
    upscale_images = []
    for time in images:
        new_time = []
        for bands in time:
            upscale_image = upscaling_sample(bands, upscale_factor)
            new_time.append(np.array(upscale_image))
        upscale_images.append(np.array(new_time))
    return np.array(upscale_images)


def flip_image(X, axis=None):
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


def augment_image(img, augmentation_index):
    if augmentation_index is None or augmentation_index == 1:
        return flip_image(img)
    if augmentation_index is None or augmentation_index == 2:
        return flip_image(img, 0)
    if augmentation_index is None or augmentation_index == 3:
        return flip_image(img, 1)
    if augmentation_index is None or augmentation_index == 4:
        return add_noise(img, ran=10)
    if augmentation_index is None or augmentation_index == 5:
        return change_bright(img, ran=10)


def augment_stack(imgs, augmentation_index):
    # Do the augmentations on images (number_occurrences, bands, height, width).
    time_aug_imgs = []
    for number_occurrences in imgs:
        aug_img = []
        for bands in number_occurrences:
            aug_img.append(augment_image(bands, augmentation_index))
        time_aug_imgs.append(aug_img)
    # Revert shapes back to (number_occurrences, height, width, bands)
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


def augment(
    X,
    Y,
    sizeX_height=None,
    sizeX_width=None,
    sizeY_height=None,
    sizeY_width=None,
    augmentation_index=None,
):
    # To make the augmentations in a standard mode we need to
    # get the tensors on the same shape, and the same number of dimensions.
    data_X = set_standard_shape(X, x_size=sizeX_height, y_size=sizeX_width)
    data_Y = set_standard_shape(Y, x_size=sizeY_height, y_size=sizeY_width)
    data_Y = np.squeeze(data_Y)
    data_X = np.squeeze(data_X)
    if len(data_X.shape) < 4:
        data_X = np.expand_dims(data_X, list(np.arange(4 - len(data_X.shape))))
    if len(data_Y.shape) < 4:
        data_Y = np.expand_dims(data_Y, list(np.arange(4 - len(data_Y.shape))))
    resulted_augmentation_X = [X[0]]
    resulted_augmentation_Y = [Y]
    for i in augmentation_index:
        resulted_augmentation_X.append(augment_stack(data_X, i))
        resulted_augmentation_Y.append(augment_stack(data_Y, i))
    resulted_augmentation_Y = np.squeeze(resulted_augmentation_Y)
    return (
        resulted_augmentation_X,
        resulted_augmentation_Y,
    )
    # Flip
    # Add noise
    # brightness_range # ran > 1  Brightness of Image increases


def batch_augment(
    X,
    Y,
    sizeX_height,
    sizeX_width,
    sizeY_height,
    sizeY_width,
    augmentation_index=1,
    batch_size=1,
    mode="3D_Model",
):
    """
    Define how many augmentations to do, and build the correct input for the augmentation function

    Parameters
    ----------
        X : numpy array
            Set of collected images.
        Y : numpy array
            Goal image in training.
        augmentation_index : int or list
            Set the number of augmentations. If it is a list, does the augmentations
            with the keys on the list, if it is an int, does all the keys up to that.
            keys:
                0: No augmentation
                1, 2, 3: flips
                4: noise
                5: bright
    Returns
    -------
        augmentedX, augmentedY : numpy array
            Augmented images.
    """
    if isinstance(augmentation_index, int):
        augmentation_index = np.arange(augmentation_index) + 1
    batch_X = np.array([])
    batch_Y = np.array([])
    if mode == "2D_Model":
        X = np.expand_dims(X, 1)
    for batch in range(batch_size):
        aug_X, aug_Y = augment(
            X[batch : batch + 1],
            Y[batch : batch + 1],
            sizeX_height=sizeX_height,
            sizeX_width=sizeX_width,
            sizeY_height=sizeY_height,
            sizeY_width=sizeY_width,
            augmentation_index=augmentation_index,
        )
        if not batch_X.any():
            batch_X = np.array(aug_X)
            batch_Y = np.array(aug_Y)
        else:
            batch_X = np.concatenate([batch_X, aug_X])
            batch_Y = np.concatenate([batch_Y, aug_Y])
    if mode == "2D_Model":
        batch_X = np.vstack(batch_X)
    if len(batch_Y.shape) < 4:
        batch_Y = np.expand_dims(batch_Y, -1)

    return batch_X, batch_Y
