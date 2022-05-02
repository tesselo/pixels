import math
import os

import geopandas as gp
import numpy as np
import rasterio
from rasterio import merge
from rasterio.warp import Resampling
from rasterio.windows import Window
from shapely.geometry import box

from pixels.const import FLOAT_NODATA_VALUE, INTEGER_NODATA_VALUE
from pixels.generator.generator_utils import read_raster_meta
from pixels.generator.stac_utils import list_files_in_folder, upload_files_s3
from pixels.log import logger
from pixels.utils import load_dictionary


def check_overlaping_features(predictions_bbox):
    """Check if the given shapes have any overlaped features.

    Parameters
    ----------
    predictions_bbox : GeoDataFrame
        Vector containing the shapes to analyse.

    Returns
    -------
    bool
    """
    overlaping_feats = np.sum(
        gp.sjoin(predictions_bbox, predictions_bbox, "left", predicate="overlaps")[
            "index_right"
        ]
    )
    return overlaping_feats > 0


def get_rasters_bbox(rasters):
    """Creates a GeoDataFrame with all the boundings boxes of the given rasters.

    Parameters
    ----------
    rasters : list (paths)
        List of paths to rasters.

    Returns
    -------
    df : GeoDataFrame
        Bounding boxes of input rasters.
    """
    df = gp.GeoDataFrame(columns=["location", "geometry"])
    for path in rasters:
        with rasterio.open(path) as src:
            bounds = src.bounds
            geom = box(bounds[0], bounds[1], bounds[2], bounds[3])
            meta = src.meta
            df = df.append({"location": path, "geometry": geom}, ignore_index=True)
    df = df.set_crs(meta["crs"])

    return df


def custom_merge_sum(
    merged_data,
    new_data,
    merged_mask,
    new_mask,
    index=None,
    roff=None,
    coff=None,
):
    """Merge method for rasterio.merge.
    https://rasterio.readthedocs.io/en/latest/api/rasterio.merge.html#rasterio.merge.merge
    The result raster will be the value sum of given rasters.

    Parameters
    ----------
    merged_dataarray_like
        array to update with new_data
    new_dataarray_like
        data to merge same shape as merged_data
    merged_mask, new_maskarray_like
        boolean masks where merged/new data pixels are invalid same shape as merged_data
    index: int
        index of the current dataset within the merged dataset collection
    roff: int
        row offset in base array
    coff: int
        column offset in base array

    """
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.add(merged_data, new_data, out=merged_data, where=mask, casting="unsafe")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def custom_merge_count(
    merged_data,
    new_data,
    merged_mask,
    new_mask,
    index=None,
    roff=None,
    coff=None,
):
    """Merge method for rasterio.merge.
    https://rasterio.readthedocs.io/en/latest/api/rasterio.merge.html#rasterio.merge.merge
    The result raster will be the number of existing valid pixels in the given rasters.

    Parameters
    ----------
    merged_dataarray_like
        array to update with new_data
    new_dataarray_like
        data to merge same shape as merged_data
    merged_mask, new_maskarray_like
        boolean masks where merged/new data pixels are invalid same shape as merged_data
    index: int
        index of the current dataset within the merged dataset collection
    roff: int
        row offset in base array
    coff: int
        column offset in base array

    """
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.add(merged_data, mask, out=merged_data, where=mask, casting="unsafe")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, mask, where=mask, casting="unsafe")


def build_overviews_and_tags(raster_path, tags=None):
    with rasterio.open(raster_path) as src:
        raster_meta = src.meta
    factor_max = min(raster_meta["height"], raster_meta["width"])
    factors = [(2 ** a) for a in range(1, 7) if (2 ** a) < factor_max]
    if "int" in str(raster_meta["dtype"]).lower():
        resampling = Resampling.nearest
    else:
        resampling = Resampling.average
    with rasterio.open(raster_path, "r+", **raster_meta) as dst:
        if tags is not None:
            dst.update_tags(**tags)
        dst.build_overviews(factors, resampling)


def check_data_type_int(data_type):
    return np.dtype(data_type).kind in ["i", "u"]


def set_nodata_based_on_dtype(data_type):
    if check_data_type_int(data_type):
        return INTEGER_NODATA_VALUE
    return FLOAT_NODATA_VALUE


def chunk_output(width, height, count, itemsize, mem_limit=1):
    """Divide the calculation output into chunks

    This function determines the chunk size such that an array of shape
    (chunk_size, chunk_size, count) with itemsize bytes per element
    requires no more than mem_limit megabytes of memory.

    Output chunks are described by rasterio Windows.

    Parameters
    ----------
    width : int
        Output width
    height : int
        Output height
    count : int
        Number of output bands
    itemsize : int
        Number of bytes per pixel
    mem_limit : int, default
        The maximum size in memory of a chunk array

    Returns
    -------
    list of sequences of Windows
    """
    max_pixels = mem_limit * 1.0e6 / itemsize * count
    chunk_size = int(math.floor(math.sqrt(max_pixels)))
    ncols = int(math.ceil(width / chunk_size))
    nrows = int(math.ceil(height / chunk_size))
    chunk_windows = []

    for col in range(ncols):
        col_offset = col * chunk_size
        w = min(chunk_size, width - col_offset)
        for row in range(nrows):
            row_offset = row * chunk_size
            h = min(chunk_size, height - row_offset)
            chunk_windows.append(((row, col), Window(col_offset, row_offset, w, h)))

    return chunk_windows


def raster_calc(
    command,
    files,
    output,
    driver=None,
    name=None,
    dtype=None,
    masked=None,
    overwrite=True,
    mem_limit=1,
    creation_options={},
    command_args={},
):

    """
    Python implementation of gdal_calc. Based on:
    https://github.com/rasterio/rasterio/blob/master/rasterio/rio/calc.py
    Accepts a list of rasters with the same profile (extension and crs).
    Iterates over a moving window on all these files making the given command
    and writing the window result on the output file.
    """

    # Get commmand from numpy.
    if hasattr(np, command):
        command = getattr(np, command)
    else:
        raise ValueError(
            "Calc command is not defined in numpy. No other commands allowed."
        )

    # Open 1st file in list to get profile.
    with rasterio.open(files[0]) as src:
        kwargs = src.profile
        meta = src.meta
        img = src.read()

    kwargs.update(**creation_options)
    dtype = dtype or meta["dtype"]
    nodata = set_nodata_based_on_dtype(dtype)
    kwargs["dtype"] = dtype
    kwargs["nodata"] = nodata
    kwargs.pop("driver", None)
    if driver:
        kwargs["driver"] = driver

    dst = None
    work_windows = [(None, Window(0, 0, 16, 16))]
    for ij, window in work_windows:
        images = []
        for path in files:
            with rasterio.open(path) as src:
                src_meta = src.meta
                if masked is None:
                    masked = src_meta["nodata"]
                img = src.read(masked=masked, window=window)
                images.append(img)
        results = command(*images, **command_args)
        results = results.astype(dtype)
        if isinstance(results, np.ma.core.MaskedArray):
            results = results.filled(float(kwargs["nodata"]))
            if len(results.shape) == 2:
                results = np.ma.asanyarray([results])
        elif len(results.shape) == 2:
            # Ensure nodata when command ignores it.
            if np.any(images[0].mask[0]):
                results[images[0].mask[0]] = kwargs["nodata"]
            results = np.asanyarray([results])

        if dst is None:
            kwargs["count"] = results.shape[0]
            dst = rasterio.open(output, "w", **kwargs)
            work_windows.extend(
                chunk_output(
                    dst.width,
                    dst.height,
                    dst.count,
                    np.dtype(dst.dtypes[0]).itemsize,
                    mem_limit=mem_limit,
                )
            )
        # In subsequent iterations we write results.
        else:
            dst.write(results, window=window)


def merge_all(
    files_to_merge,
    out_type="Byte",
    no_data=None,
    res="average",
    method="first",
    merger_folder=None,
    prediction_name=None,
    additional_kwrgs={},
):
    if check_data_type_int(out_type):
        # No predictor (1, default)
        # Horizontal differencing (2)
        # Floating point predition (3)
        # https://gdal.org/drivers/raster/gtiff.html?highlight=predictor#creation-options
        predictor = 2
    else:
        predictor = 3
    if not no_data:
        no_data = set_nodata_based_on_dtype(out_type)

    if prediction_name is None:
        if merger_folder is None:
            prediction_name = os.path.join("merger_files", "merged_prediction.tif")
        else:
            prediction_name = os.path.join(merger_folder, "merged_prediction.tif")

    merge.merge(
        files_to_merge,
        nodata=no_data,
        dtype=out_type,
        method=method,
        resampling=rasterio.enums.Resampling[res],
        dst_path=prediction_name,
        dst_kwds={
            "COMPRESS": "DEFLATE",
            "PREDICTOR": predictor,
            "NUM_THREADS": "ALL_CPUS",
            "BIGTIFF": "IF_NEEDED",
            "TILED": "YES",
            "dtype": out_type,
        },
        **additional_kwrgs,
    )
    build_overviews_and_tags(prediction_name, tags=None)

    return prediction_name


def merge_overlaping(
    files_to_merge,
    out_type="Byte",
    no_data=None,
    merger_folder=None,
):
    if merger_folder is None:
        merger_folder = "merger_files"
    merged_sum_path = os.path.join(merger_folder, "merged_predictions_sum.tif")
    merged_count_path = os.path.join(merger_folder, "merged_predictions_count.tif")
    outfile = os.path.join(merger_folder, "predictions_ovelaped_merge.tif")
    logger.info("Building sum raster.")

    merged_sum_path = merge_all(
        files_to_merge,
        out_type=out_type,
        no_data=no_data,
        res="average",
        method=custom_merge_sum,
        prediction_name=merged_sum_path,
    )
    logger.info("Building count raster.")
    no_data_count = INTEGER_NODATA_VALUE
    out_type_count = "uint8"
    merged_count_path = merge_all(
        files_to_merge,
        out_type=out_type_count,
        no_data=no_data_count,
        res="average",
        method=custom_merge_count,
        prediction_name=merged_count_path,
        additional_kwrgs={"indexes": [1]},
    )
    calc = "divide"
    out_type = f"{out_type[0].upper()}{out_type[1:]}"
    logger.info("Building average raster.")
    raster_calc(calc, [merged_sum_path, merged_count_path], outfile, mem_limit=64)

    build_overviews_and_tags(outfile, tags=None)
    return outfile


def merge_prediction(generator_config_uri):
    """Merge all predictions in the given prediction key folder.
    On overlaped rasters makes an average of all values.
    Builds a geopackage file with the bounding boxes of the predictions tiles.
    In case the images are probabilities it builds the full probability map and the classes from it.
    In case there are overlaping images it will build a map containing the sum of all raster and the count.

    Limitation:
    Right now it will merge all files in the folder, which means that if there are multiple timesteps they will be averege out.
    TODO: Build multiple timesteps loop.

    Parameters
    ----------
    generator_config_uri : string (path)
        Path to P2 prediction generator configuration file.

    """
    predict_path = os.path.dirname(generator_config_uri)

    prediction_folder = os.path.join(predict_path, "predictions")
    prediction_generator_conf = load_dictionary(generator_config_uri)
    extract_probabilities = prediction_generator_conf.get(
        "extract_probabilities", False
    )
    num_classes = prediction_generator_conf.get("num_classes", False)

    categorical = not extract_probabilities or num_classes == 1
    logger.info("Listing prediction files.")
    prediction_files = list_files_in_folder(prediction_folder, filetype=".tif")

    raster_meta = read_raster_meta(prediction_files[0])

    if predict_path.startswith("s3"):
        merger_files_folder = predict_path.replace("s3://", "tmp/")
    merger_files_folder = os.path.join(merger_files_folder, "merger_files")
    os.makedirs(merger_files_folder, exist_ok=True)
    logger.info("Building vector of tiles bboxes.")
    predictions_bbox = get_rasters_bbox(prediction_files)
    predictions_bbox_path = os.path.join(merger_files_folder, "predictions_bbox.gpkg")
    predictions_bbox.to_file(predictions_bbox_path, driver="GPKG")
    if not check_overlaping_features(predictions_bbox) or categorical:
        logger.info("Non overlaping or categorical rasters. Merging all.")
        merged_path = merge_all(
            prediction_files,
            out_type=raster_meta["dtype"],
            no_data=raster_meta["nodata"],
            merger_folder=merger_files_folder,
        )
    else:
        logger.info("Merging overlaping features.")
        merged_path = merge_overlaping(
            prediction_files,
            out_type=raster_meta["dtype"],
            no_data=raster_meta["nodata"],
            merger_folder=merger_files_folder,
        )
    predictions_bbox = None
    if extract_probabilities:
        logger.info("Extrating probabilities. Building class raster.")
        calc = "argmax"
        command_args = {"axis": 0}
        outfile = os.path.join(merger_files_folder, "merged_predictions_classes.tif")
        raster_calc(
            calc,
            [merged_path],
            outfile,
            command_args=command_args,
            dtype="uint8",
            mem_limit=64,
        )

    if predict_path.startswith("s3"):
        logger.info("Saving files to S3.")
        upload_files_s3(merger_files_folder, file_type="")
