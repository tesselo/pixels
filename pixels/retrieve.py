import numpy
import rasterio
import structlog
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from pixels.const import NODATA_VALUE
from pixels.utils import compute_mask, compute_transform

logger = structlog.get_logger(__name__)


def retrieve(
    source,
    geojson,
    scale=None,
    discrete=False,
    clip=False,
    all_touched=False,
    bands=None,
):
    """
    Get pixels from a source raster over the a geojson feature collection.

    Parameters
    ----------
    source : str
        The raster source location, can be local, html or s3 paths. Anything
        that rasterio can open.
    geojson : dict
        The area over which the raster data will be collected. The geometry
        extent will be used as bounding box for the raster. A custom CRS
        property can be used to define the projection.
    scale : int or float, optional
        The scale (resolution) of the output raster. This number needs to be in
        the uints of the input geojson. If not provided, the scale of the input
        raster is used, but only if the projection of the raster is the same as
        the projection of the geojson.
    discrete : bool, optional
        If True, the input raster file is assumed to be discrete (ingeger). The
        resampling strategy is nearest neighbor for discrete rasters, and
        bilinear for continuous rasters.
    clip : boolean, optional
        If True, the raster is clipped against the geometry. All values outside
        the geometry will be set to nodata.
    all_touched : boolean, optional
        If True, the all_touched option will be used when rasterizing the
        geometries. Ignored if clip is False.
    bands : list of int, optional
        Defines which band indices shall be extracted from the source raster. If
        it is empty or None, all bands will be extracted.

    Returns
    -------
    creation_args : dict
        The creation arguments metadata for the extracted pixel matrix. Can be
        used to write the extracted pixels to a file if desired.
    pixels : array
        The extracted pixel array, with a shape (bands, height, width). The
        pixels value is returned as None, if there is no data in the result.
    """
    logger.debug("Retrieving {}".format(source))

    # Validate geojson by opening it with rasterio CRS class.
    dst_crs = CRS.from_dict(geojson["crs"])

    # Determine resampling algorithm.
    resampling = Resampling.nearest if discrete else Resampling.bilinear
    # Open remote raster.
    with rasterio.open(source) as src:
        # If no scale was provided, use the source scale as the target scale.
        if not scale:
            if src.crs and src.crs == dst_crs:
                scale = abs(src.transform[0])
            else:
                raise ValueError(
                    "Can not auto-determine target scale because"
                    "the geom crs does not match the source crs."
                )
        logger.debug("Source CRS is {}.".format(src.crs))

        # If no band indices were provided, process all bands.
        if not bands:
            bands = range(1, src.count + 1)
        elif isinstance(bands, int):
            bands = [bands]

        # Prepare target raster transform from the geometry input.
        transform, width, height = compute_transform(geojson, scale)
        logger.debug("Target array shape is ({}, {})".format(height, width))

        # Prepare creation parameters for memory raster.
        creation_args = src.meta.copy()
        creation_args.update(
            {
                "driver": "GTiff",
                "crs": dst_crs,
                "transform": transform,
                "width": width,
                "height": height,
            }
        )

        # Set different band count if bands were given as input.
        if bands:
            creation_args["count"] = len(bands)

        # Open memory destination file.
        with MemoryFile() as memfile:
            with memfile.open(**creation_args) as dst:
                # Prepare projection arguments.
                proj_args = {
                    "dst_transform": transform,
                    "dst_crs": dst_crs,
                    "resampling": resampling,
                }

                # Determine georeferencing from source raster.
                if src.crs:
                    # Extract source crs directly.
                    src_crs = src.crs
                else:
                    # Extract georeference points and source crs from gcps.
                    # This is the case for Sentinel-1, for instance.
                    src_gcps, src_crs = src.gcps
                    proj_args["gcps"] = src.gcps[0]

                # Set source crs.
                proj_args["src_crs"] = src_crs

                # Transform raster bands from source to destination.
                for index, band in enumerate(bands):
                    proj_args.update(
                        {
                            "source": rasterio.band(src, band),
                            "destination": rasterio.band(dst, index + 1),
                        }
                    )
                    reproject(**proj_args)

                # Get pixel values from reprojected raster.
                pixels = dst.read()

        if clip:
            mask = compute_mask(
                geojson, height, width, transform, all_touched=all_touched
            )
            # Apply mask to all bands.
            pixels[:, mask] = NODATA_VALUE

        # If only one band was requested, reshape result to 2D array.
        if len(bands) == 1:
            pixels = pixels[bands[0] - 1]

        # Set empty results to None to save memory.
        if numpy.all(pixels == NODATA_VALUE):
            pixels = None

        # Return re-creation args and pixel data.
        return creation_args, pixels
