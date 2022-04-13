import os

import geopandas as gp
import numpy as np
import rasterio
from rasterio import merge
from rasterio.rio.calc import _chunk_output
from rasterio.warp import Resampling
from rasterio.windows import Window
from shapely.geometry import box

from pixels.generator.generator_utils import read_raster_meta
from pixels.generator.stac_utils import (
    _load_dictionary,
    list_files_in_folder,
    upload_files_s3,
)
from pixels.log import logger

INTEGER_NODATA_VALUE = 255
FLOAT_NODATA_VALUE = -9999


def check_overlaping_features(predictions_bbox):
    overlaping_feats = np.sum(
        gp.sjoin(predictions_bbox, predictions_bbox, "left", predicate="overlaps")[
            "index_right"
        ]
    )
    if overlaping_feats > 0:
        return True
    else:
        return False


def get_tiles_bbox(list_rasters):
    df = gp.GeoDataFrame(columns=["location", "geometry"])
    for path in list_rasters:
        with rasterio.open(path) as src:
            bounds = src.bounds
            geom = box(bounds[0], bounds[1], bounds[2], bounds[3])
            meta = src.meta
            df = df.append({"location": path, "geometry": geom}, ignore_index=True)
    df = df.set_crs(meta["crs"])

    return df


def custom_merge_sum(
    merged_dataarray_like,
    new_dataarray_like,
    merged_mask,
    new_maskarray_like,
    index=None,
    roff=None,
    coff=None,
):
    merged_dataarray_like[merged_mask] = np.nan
    merged_dataarray_like[:] = np.nansum(
        [merged_dataarray_like, new_dataarray_like], axis=0
    )


def custom_merge_count(
    merged_dataarray_like,
    new_dataarray_like,
    merged_mask,
    new_maskarray_like,
    index=None,
    roff=None,
    coff=None,
):
    new = new_dataarray_like
    new[new == new] = 1
    merged_dataarray_like[merged_mask] = 0
    merged_dataarray_like[:] = np.nansum([new, merged_dataarray_like], axis=0)


def build_overviews_and_tags(raster_path, tags=None):
    with rasterio.open(raster_path) as src:
        raster_meta = src.meta
    factor_max = min(raster_meta["height"], raster_meta["width"])
    factors = [(2 ** a) for a in range(1, 7) if (2 ** a) < factor_max]
    # Determine resampling type for overviews.
    if "int" in str(raster_meta["dtype"]).lower():
        resampling = Resampling.nearest
    else:
        resampling = Resampling.average
    with rasterio.open(raster_path, "r+", **raster_meta) as dst:
        # Set the given metadata tags.
        if tags is not None:
            dst.update_tags(**tags)
        dst.build_overviews(factors, resampling)


def check_data_type_int(data_type):
    if "int" in data_type.lower() or "byte" in data_type.lower():
        return True
    else:
        return False


def set_nodata_based_on_dtype(data_type):
    if check_data_type_int(data_type):
        return INTEGER_NODATA_VALUE
    else:
        return FLOAT_NODATA_VALUE


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
    # TODO: add custom commands in else.
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
                img = src.read(masked=masked, window=window)
                images.append(img)

        results = command(*images, **command_args)

        results = results.astype(dtype)
        if isinstance(results, np.ma.core.MaskedArray):
            results = results.filled(float(kwargs["nodata"]))
            if len(results.shape) == 2:
                results = np.ma.asanyarray([results])
        elif len(results.shape) == 2:
            results = np.asanyarray([results])

        if dst is None:
            kwargs["count"] = results.shape[0]
            dst = rasterio.open(output, "w", **kwargs)
            work_windows.extend(
                _chunk_output(
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
    return


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

    # There was no way to get a custom method to do the average.
    # And the vrt python thingy was prone to error.
    # Solution:
    # This makes a raster with the sum of every value and a raster with its count.
    # For the average is sum/count.
    if merger_folder is None:
        merged_sum_path = os.path.join("merger_files", "merged_predictions_sum.tif")
        merged_count_path = os.path.join("merger_files", "merged_predictions_count.tif")
        outfile = os.path.join("merger_files", "predictions_ovelaped_merge.tif")

    else:
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
    raster_calc(calc, [merged_sum_path, merged_count_path], outfile, mem_limit=5)

    build_overviews_and_tags(outfile, tags=None)
    return outfile


def merge_prediction(generator_config_uri):
    # TODO: multiple timesteps predicitons not working
    predict_path = os.path.dirname(generator_config_uri)

    prediction_folder = os.path.join(predict_path, "predictions")
    # Check prediction configuration.
    prediction_generator_conf = _load_dictionary(generator_config_uri)
    extract_probabilities = prediction_generator_conf.pop(
        "extract_probabilities", False
    )
    num_classes = prediction_generator_conf.pop("num_classes", False)

    # Check if categorical data.
    categorical = not extract_probabilities or num_classes == 1
    # Get predictions files.
    logger.info("Listing prediction files.")
    prediction_files = list_files_in_folder(prediction_folder, filetype=".tif")

    raster_meta = read_raster_meta(prediction_files[0])

    if predict_path.startswith("s3"):
        merger_files_folder = predict_path.replace("s3://", "tmp/")
    merger_files_folder = os.path.join(merger_files_folder, "merger_files")
    os.makedirs(merger_files_folder, exist_ok=True)
    # Build a file containing all the bounding boxes of the tiles.
    logger.info("Building vector of tiles bboxes.")
    predictions_bbox = get_tiles_bbox(prediction_files)
    predictions_bbox_path = os.path.join(merger_files_folder, "predictions_bbox.gpkg")
    predictions_bbox.to_file(predictions_bbox_path, driver="GPKG")

    # Merge all tifs, goes for categorical data or no overlaping.
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
            mem_limit=5,
        )

    if predict_path.startswith("s3"):
        logger.info("Saving files to S3.")
        upload_files_s3(merger_files_folder, file_type="")
