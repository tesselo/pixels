import numpy as np

from pixels.clouds import _composite_or_cloud


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


def _order_tensor_on_masks(image, mask_value, number_images=12):
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
    ind = np.sort(np.argsort(mask_count)[:number_images])
    return np.array(image[ind])


def order_tensor_on_cloud_mask(
    images,
    number_images,
    bands_index=None,
):
    bands_index = bands_index or {
        "B02": 0,
        "B03": 1,
        "B04": 2,
        "B08": 6,
        "B8A": 7,
        "B11": 8,
        "B12": 9,
    }
    B02 = images[:, bands_index["B02"]]
    B03 = images[:, bands_index["B03"]]
    B04 = images[:, bands_index["B04"]]
    B08 = images[:, bands_index["B08"]]
    B8A = images[:, bands_index["B8A"]]
    B11 = images[:, bands_index["B11"]]
    B12 = images[:, bands_index["B12"]]
    mask_img = _composite_or_cloud(
        B02,
        B03,
        B04,
        B08,
        B8A,
        B11,
        B12,
        cloud_only=True,
        light_clouds=False,
        snow=True,
        shadow_threshold=0.2,
    )
    mask_count = np.sum(mask_img, axis=(1, 2))
    ind = np.sort(np.argsort(mask_count)[:number_images])
    return np.array(images[ind])
