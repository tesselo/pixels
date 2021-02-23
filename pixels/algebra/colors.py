"""
Functions ported directly from django-raster.

Source: https://github.com/geodesign/django-raster/blob/master/raster/utils.py
"""
import numpy


def rescale_to_channel_range(data, dfrom, dto, dover=None):
    """
    Rescales an array to the color interval provided.

    Assumes that the data is normalized. This is used as a helper function for
    continuous colormaps.

    Parameters
    ----------
    data : array
        Normalized numpy array to use as scaling for colors.
    dfrom : int
        Start color range value. Must be between 0 and 255.
    dto : int
        End color range value. Must be between 0 and 255.
    dover : int, optional
        Middle color range value. Must be between 0 and 255.

    Returns
    -------
    data : array
        The rescaled values adapted to color ranges.
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


def colorize(data, colormap):
    """
    Creates an python image from pixel values of a GDALRaster.

    The input is a dictionary that maps pixel values to RGBA UInt8 colors.
    If an interpolation interval is given, the values are. Example colormap:

    ```json
    {
        "continuous": "True",
        "from": [255, 0, 0],
        "to": [0, 0, 255],
        "over": [0, 255, 0],
        "range": [0, 100]
    }
    ```

    Parameters
    ----------
    data : array
        Data to use for colorization. Should be a 2D array.
    colormap : dict
        Colormap to be applied.

    Returns
    -------
    rgba : array
        Colorized image data as RGBA array.
    """
    # Get data as 1D array.
    dat = data.ravel()
    stats = {}

    if "continuous" in colormap:
        dmin, dmax = colormap.get("range", (dat.min(), dat.max()))

        if dmax == dmin:
            norm = dat == dmin
        else:
            norm = (dat - dmin) / (dmax - dmin)

        color_from = colormap.get("from", [0, 0, 0])
        color_to = colormap.get("to", [1, 1, 1])
        color_over = colormap.get("over", [None, None, None])

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
        if numpy.ma.is_masked(dat):
            alpha = 255 * numpy.logical_not(dat.mask) * (norm >= 0) * (norm <= 1)
        else:
            alpha = 255 * (norm > 0) * (norm < 1)

        rgba = numpy.array([red, green, blue, alpha], dtype="uint8").T
    else:
        # Create zeros array.
        rgba = numpy.zeros((dat.shape[0], 4), dtype="uint8")

        # Replace matched rows with colors.
        for key, color in colormap.items():
            orig_key = key
            # Try to use the key as number directly.
            key = float(key)
            selector = dat == key
            # If masked, use mask to filter values additional to formula values.
            if numpy.ma.is_masked(selector):
                selector.fill_value = False
                rgba[selector.filled() == 1] = color
                # Compress for getting statistics.
                selector = selector.compressed()
            else:
                rgba[selector] = color

            # Track pixel statistics for this tile.
            stats[orig_key] = int(numpy.sum(selector))

    # Reshape array to image size.
    rgba = rgba.reshape(data.shape[0], data.shape[1], 4)

    return rgba, stats
