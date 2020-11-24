import os
from io import BytesIO

import numpy
import rasterio
from PIL import Image, ImageDraw, ImageEnhance

from pixels import algebra, const
from pixels.exceptions import PixelsFailed


def rescale_to_channel_range(data, dfrom, dto, dover=None):
    """
    Rescales an array to the color interval provided. Assumes that the data is normalized.
    This is used as a helper function for continuous colormaps.
    """
    # If the interval is zero dimensional, return constant array.
    if dfrom == dto:
        return numpy.ones(data.shape) * dfrom

    if dover is None:
        # Invert data going from smaller to larger if origin color is bigger
        # than target color.
        if dto < dfrom:
            data = 1 - data
        return data * abs(dto - dfrom) + min(dto, dfrom)
    else:
        # Divide data in upper and lower half.
        lower_half = data < 0.5
        # Recursive calls to scaling upper and lower half separately.
        data[lower_half] = rescale_to_channel_range(data[lower_half] * 2, dfrom, dover)
        data[numpy.logical_not(lower_half)] = rescale_to_channel_range(
            (data[numpy.logical_not(lower_half)] - 0.5) * 2, dover, dto
        )

    return data


def hex_to_rgba(value, alpha=255):
    """
    Converts a HEX color string to a RGBA 4-tuple.
    """
    if value is None:
        return [None, None, None]

    value = value.lstrip("#")

    # Check length and input string property
    if len(value) not in [1, 2, 3, 6] or not value.isalnum():
        raise PixelsFailed("Invalid color, could not convert hex to rgb.")

    # Repeat values for shortened input
    value = (value * 6)[:6]

    # Convert to rgb
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def get_s2_rgb_pixels(projectid, z, x, y):
    try:
        with rasterio.open(
            "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!B04.tif".format(
                const.BUCKET, projectid, z, x, y
            )
        ) as rst:
            red = rst.read(1)
        with rasterio.open(
            "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!B03.tif".format(
                const.BUCKET, projectid, z, x, y
            )
        ) as rst:
            green = rst.read(1)
        with rasterio.open(
            "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!B02.tif".format(
                const.BUCKET, projectid, z, x, y
            )
        ) as rst:
            blue = rst.read(1)
        mask = numpy.all((red != 0, blue != 0, green != 0), axis=0).T * 255
        return red, green, blue, mask
    except rasterio.errors.RasterioIOError:
        return


def get_s1_rgb_pixels(projectid, z, x, y):

    try:
        with rasterio.open(
            "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!VV.tif".format(
                const.BUCKET, projectid, z, x, y
            )
        ) as rst:
            red = rst.read(1)
        with rasterio.open(
            "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!VH.tif".format(
                const.BUCKET, projectid, z, x, y
            )
        ) as rst:
            green = rst.read(1)
    except rasterio.errors.RasterioIOError:
        try:
            with rasterio.open(
                "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!HH.tif".format(
                    const.BUCKET, projectid, z, x, y
                )
            ) as rst:
                red = rst.read(1)
            with rasterio.open(
                "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!HV.tif".format(
                    const.BUCKET, projectid, z, x, y
                )
            ) as rst:
                green = rst.read(1)
        except:
            return

    mask = numpy.all((red != 0, green != 0), axis=0).T * 255

    # Transform the data to provide an interpretable visual result.
    red = numpy.log(red)
    green = numpy.log(green)

    red = (red / 7) * const.SENTINEL_2_RGB_CLIPPER
    green = (green / 7) * const.SENTINEL_2_RGB_CLIPPER
    blue = (red / green) * const.SENTINEL_2_RGB_CLIPPER / 2

    return red, green, blue, mask


def get_s2_formula_pixels(
    projectid, z, x, y, formula, color_from, color_to, color_over, dmin, dmax, frmt
):
    # Instantiate formula parser.
    parser = algebra.FormulaParser()
    data = {}
    # Get pixels for all bands present in formula.
    for band in const.SENTINEL_2_BANDS:
        if band in formula:
            try:
                with rasterio.open(
                    "zip+s3://{}/{}/tiles/{}/{}/{}/pixels.zip!{}.tif".format(
                        const.BUCKET, projectid, z, x, y, band
                    )
                ) as rst:
                    data[band] = rst.read(1).T.astype("float")
            except rasterio.errors.RasterioIOError:
                return

    index = parser.evaluate(data, formula)

    if frmt == "tif":
        index = index.reshape(256, 256).T
        return index

    if dmax == dmin:
        norm = index == dmin
    else:
        norm = (index - dmin) / (dmax - dmin)

    color_from = hex_to_rgba(color_from)
    color_to = hex_to_rgba(color_to)
    color_over = hex_to_rgba(color_over)

    red = rescale_to_channel_range(
        norm.copy(), color_from[0], color_to[0], color_over[0]
    )
    green = rescale_to_channel_range(
        norm.copy(), color_from[1], color_to[1], color_over[1]
    )
    blue = rescale_to_channel_range(
        norm.copy(), color_from[2], color_to[2], color_over[2]
    )

    # Compute alpha channel from mask if available.
    mask = numpy.all([dat != 0 for dat in data.values()], axis=0) * 255

    return red, green, blue, mask


def get_empty_image(z):
    output = BytesIO()
    path = os.path.dirname(os.path.abspath(__file__))
    # Open the ref image.
    img = Image.open(os.path.join(path, "assets/tesselo_empty.png"))
    # Write zoom message into image.
    if z > 14:
        msg = "Zoom is {} | Max zoom is 14".format(z)
    else:
        msg = "No Data"
    draw = ImageDraw.Draw(img)
    text_width, text_height = draw.textsize(msg)
    draw.text(
        ((img.width - text_width) / 2, 60 + (img.height - text_height) / 2),
        msg,
        fill="black",
    )
    # Save image to io buffer.
    img.save(output, format="PNG")
    output.seek(0)
    return output


def get_image_from_pixels(pixpix, enhance=False):
    output = BytesIO()
    # Create image object.
    img = Image.fromarray(pixpix.T)
    # Enhance color scheme for RGB mode.
    if enhance:
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Brightness(img).enhance(1.8)
        img = ImageEnhance.Color(img).enhance(1.4)

    # Save image to io buffer.
    img.save(output, format=const.REQUEST_FORMAT_PNG)
    output.seek(0)
    return output
