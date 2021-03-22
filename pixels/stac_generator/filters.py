import numpy as np


def _make_mask_on_value(img, mask_value):
    """
    Based on a value create a mask in an image.

    Parameters
    ----------
        img : array
            Image array.
        mask_value : float, int
            Value to create mask.

    Returns
    -------
        mask_img : numpy array
            The mask.
    """
    mask_img = img == mask_value
    return mask_img


def _order_tensor_on_masks(image, mask_value):
    """
    Order a set of images based on a mask count.

    Parameters
    ----------
        img : array
            Image array.
        mask_value : float, int
            Value to create mask.

    Returns
    -------
        image : numpy array
            The ordered set of images.
    """
    mask_img = _make_mask_on_value(image, mask_value)
    mask_count = np.sum(mask_img, axis=(1, 2, 3))
    ind = np.argsort(mask_count)
    return np.array(image[ind])
