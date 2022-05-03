import numpy as np

from pixels.clouds import _composite_or_cloud, landsat_cloud_mask
from pixels.const import LANDSAT_8, SENTINEL_2
from pixels.exceptions import InconsistentGeneratorDataException


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


def sentinel_2_cloud_mask(images, bands_index):
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
    return mask_img


def order_tensor_on_masks(images, mask_value, max_images=12):
    """
    Order a set of images based on a mask count.

    Parameters
    ----------
        images : array
            Image array.
        mask_value : float, int
            Value to create mask.
        max_images : int
            The maximum number of images to return

    Returns
    -------
        image : numpy array
            The ordered set of images.
    """
    mask_img = _make_mask_on_value(images, mask_value)
    mask_count = np.sum(mask_img, axis=(1, 2, 3))
    ind = np.sort(np.argsort(mask_count)[:max_images])
    return np.array(images[ind])


def order_tensor_on_cloud_mask(
    images,
    max_images,
    bands_index=None,
    sat_platform=SENTINEL_2,
):
    """
    Order a set of images based on a cloud mask.

    Parameters
    ----------
        images : array
            Image array.
        max_images : int
            The maximum number of images to return
        bands_index: dict
            A dictionary with the cloud bands

    Returns
    -------
        image : numpy array
            The ordered set of images.
    """
    bands_index = bands_index or {
        "B02": 0,
        "B03": 1,
        "B04": 2,
        "B08": 6,
        "B8A": 7,
        "B11": 8,
        "B12": 9,
    }
    if sat_platform == SENTINEL_2:
        mask_img = sentinel_2_cloud_mask(images, bands_index)
    elif sat_platform == LANDSAT_8:
        mask_img = landsat_cloud_mask(images)
    else:
        raise InconsistentGeneratorDataException(
            f"Platform {sat_platform} is not supported for cloud sorting."
        )
    mask_count = np.sum(mask_img, axis=(1, 2))
    ind = np.sort(np.argsort(mask_count)[:max_images])
    return np.array(images[ind])
