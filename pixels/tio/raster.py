import os
from dataclasses import dataclass
from io import BytesIO
from typing import Tuple

import numpy as np
import rasterio
from rasterio.enums import Resampling

from pixels.exceptions import PixelsException
from pixels.log import logger
from pixels.path import Path
from pixels.tio.virtual import is_remote, local_or_temp, open_zip, upload


def check_for_squared_pixels(rst):
    if abs(rst.transform[0]) != abs(rst.transform[4]):
        raise PixelsException(f"Pixels are not squared for raster {rst.name}")


@dataclass
class Raster:
    img: np.ndarray = None
    meta: dict = None


def write_raster(
    data,
    args,
    out_path=None,
    driver="GTiff",
    dtype="float32",
    overviews=True,
    tags=None,
):
    """
    Convert a numpy array into a raster object.

    Given a numpy array and necessary metadata, create either a raster on disk
    or return the raster in memory as a binary IO buffer. To create a file on
    disk, provide an output path.

    Parameters
    ----------
    data : array_like
        The pixel values for the raster as numpy array.
    args : dict
        Rasterio creation arguments for the new raster.
    out_path : str, optional
        The path where the new file should be written on disk. If not provided,
        a BytesIO object is returned with the raster in memory.
    driver : str, optional
        Rasterio driver for creating the new raster.
    dtype : str, optional
        Data type string specifying the output datatype.
    overviews : bool, optional
        Determines if the internal overviews will be created for the new raster.
    tags : dict, optional
        A dictionary of tags to be added to the raster file. The namespace for
        all tags will be "tesselo".

    Returns
    -------
    raster : BytesIO or None
        If an output path was provided, the raster is written on disk and None
        is returned. Otherwise, the raster is returned as a binary blob in
        memory.
    """
    # Set the raster metadata as the same as the input
    out_meta = args
    # Ensure right shape, the first dimension of the data should be the band count.
    if len(data.shape) == 2:
        data = data.reshape((1,) + data.shape)
    # Ensure correct datatype.
    data = data.astype(dtype)
    # Update some fields to ensure COG compatability.
    out_meta.update(
        {
            "count": data.shape[0],
            "dtype": dtype,
            "driver": driver,
            "tiled": "YES",
            "compress": "DEFLATE",
        }
    )
    # Determine resampling type for overviews.
    if "int" in str(dtype).lower():
        resampling = Resampling.nearest
    else:
        resampling = Resampling.average
    # Determine overview factors.
    factors = [(2**a) for a in range(1, 7) if (2**a) < min(data.shape[-2:])]
    # If a path is given write an image file on that path
    if out_path:
        with rasterio.open(out_path, "w", **out_meta) as dst:
            # Set the given metadata tags.
            dst.write(data)
            if tags:
                dst.update_tags(**tags)
            if overviews:
                dst.build_overviews(factors, resampling)
    else:
        # Returns a memory file.
        output = BytesIO()
        with rasterio.io.MemoryFile() as memfile:
            with memfile.open(**out_meta) as dst:
                # Set the given metadata tags.
                dst.write(data)
                if tags:
                    dst.update_tags(**tags)
                if overviews:
                    dst.build_overviews(factors, resampling)
            memfile.seek(0)
            output.write(memfile.read())
        output.seek(0)
        return output


def write_tiff_from_pixels_stack(date, np_img, out_path, meta):
    """
    Write raster from pixels response.

    Parameters
    ----------
        date : date object
            The date of the first scene used to create the output image.
        np_img : numpy array or None
            The extracted pixel stack, with shape (bands, height, width).
        out_path : str
            Path to folder containing the item's images.
        meta : dict
            The creation arguments metadata for the extracted pixel matrix.

    Returns
    -------
        out_path_date : str
            Path to saved raster.
    """
    out_path_date = os.path.join(out_path, date.replace("-", "_") + ".tif")
    out_path_date_tmp = local_or_temp(out_path_date)
    os.makedirs(os.path.dirname(out_path_date_tmp), exist_ok=True)
    write_raster(
        np_img,
        meta,
        out_path=out_path_date_tmp,
        dtype=np_img.dtype,
        overviews=False,
        tags={"datetime": date},
    )
    if is_remote(out_path):
        upload(out_path_date_tmp, suffix=".tif")
    return out_path_date


def read_raster(path, img=True, meta=True, zip_object=None) -> Raster:
    raster = Raster()
    try:
        parsed_path = Path(path)
        if hasattr(parsed_path, "archive") and parsed_path.archive:
            if zip_object is None:
                zip_object = open_zip(parsed_path)
            raster_file = zip_object.read(parsed_path.path.lstrip("/"))
            raster_file = BytesIO(raster_file)
        else:
            raster_file = path
        with rasterio.open(raster_file) as src:
            if img:
                check_for_squared_pixels(src)
                raster.img = src.read()
            if meta:
                raster.meta = src.meta
    except Exception as e:
        import glob

        logger.warning(f"Generator error in read_raster: {e}")
        logger.info("Files in tmp", tmp_files=glob.glob("tmp/**"))
        logger.info("Files in /tmp", tmp_files=glob.glob("/tmp/**"))
    return raster


def read_raster_meta(path, zip_object=None) -> dict:
    return read_raster(path, img=False, meta=True, zip_object=zip_object).meta


def read_raster_img(path, zip_object=None) -> np.ndarray:
    return read_raster(path, img=True, meta=False, zip_object=zip_object).img


def read_raster_tuple(path) -> Tuple[np.ndarray, dict]:
    raster = read_raster(path, img=True, meta=True)
    return raster.img, raster.meta
