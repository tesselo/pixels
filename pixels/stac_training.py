import ast
import datetime
import io
import json
import logging
import os

import h5py
import pystac
import tensorflow as tf

import pixels.stac as stc
import pixels.stac_generator.generator_class as stcgen
from pixels.utils import write_raster

logger = logging.getLogger(__name__)


def _load_dictionary(path_file):
    # Open config file and load as dict.
    if path_file.startswith("s3"):
        my_str = stc.open_file_from_s3(path_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        dict = json.loads(new_str)
    else:
        with open(path_file, "r") as json_file:
            input_config = json_file.read()
            dict = ast.literal_eval(input_config)
    return dict


def _save_and_write_tif(out_path, img, meta):
    out_path_tif = out_path
    if out_path.startswith("s3"):
        out_path_tif = out_path_tif.replace("s3://", "tmp/")
    if not os.path.exists(os.path.dirname(out_path_tif)):
        os.makedirs(os.path.dirname(out_path_tif))
    write_raster(
        img,
        meta,
        out_path=out_path_tif,
    )
    if out_path.startswith("s3"):
        stc.upload_files_s3(os.path.dirname(out_path_tif), file_type="tif")


def create_pystac_item(
    id_raster,
    footprint,
    bbox,
    datetime_var,
    out_meta,
    path_item,
    aditional_links,
    href_path,
):

    # Create stac item.
    item = pystac.Item(
        id=id_raster,
        geometry=footprint,
        bbox=bbox,
        datetime=datetime_var,
        properties=out_meta,
    )
    # Register raster as asset of item.
    item.add_asset(
        key=id_raster,
        asset=pystac.Asset(
            href=path_item,
            media_type=pystac.MediaType.GEOTIFF,
        ),
    )
    if aditional_links:
        item.add_link(pystac.Link("x_catalog", aditional_links))
    item.set_self_href(href_path)
    # Validate item.
    item.validate()
    item.save_object()
    return item


def load_model_from_file(model_configuration_file):
    # Open config file and load as dict.
    if model_configuration_file.startswith("s3"):
        my_str = stc.open_file_from_s3(model_configuration_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        input_config = json.loads(new_str)
        input_config = json.dumps(input_config)
    else:
        # Reading the model from JSON file
        with open(model_configuration_file, "r") as json_file:
            input_config = json_file.read()
    model_j = tf.keras.models.model_from_json(input_config)
    return model_j


def train_model_function(
    catalog_uri,
    model_config_uri,
    model_compile_arguments_uri,
    model_fit_arguments_uri,
    generator_arguments_uri,
):
    """
    From a catalog and the cnfigurations files build a model and train on the
    given data. Save the model.

    Parameters
    ----------
        catalog_uri : pystac catalog
            Catalog with the information where to download data.
        model_config_uri : path to json file
            File of dictonary containing the model configuration.
        model_compile_arguments_uri : path to json file
            File of dictonary containing the compilation arguments.
        model_fit_arguments_uri : path to json file
            File of dictonary containing the fit arguments.
        generator_arguments_uri : path to json file
            File of dictonary containing the generator configuration.
    Returns
    -------
        model : tensorflow trained model
            Model trained with catalog data.
    """
    # TODO: Think of a way to make img size an input.
    gen_args = _load_dictionary(generator_arguments_uri)
    dtgen = stcgen.DataGenerator_stac(catalog_uri, **gen_args)
    model = load_model_from_file(model_config_uri)
    model.compile(**_load_dictionary(model_compile_arguments_uri))
    fit_args = _load_dictionary(model_fit_arguments_uri)
    model.fit(dtgen, **fit_args)
    path_model = os.path.join(os.path.dirname(model_config_uri), "model.h5")
    # Store the model in bucket.
    if path_model.startswith("s3"):
        with io.BytesIO() as fl:
            with h5py.File(fl) as h5fl:
                model.save(h5fl)
                h5fl.flush()
                h5fl.close()
            stc.upload_obj_s3(path_model, fl.getvalue())
    else:
        with h5py.File(path_model) as h5fl:
            model.save(h5fl)

    return model


def predict_function_batch(
    model_uri,
    generator_config_uri,
    collection_uri,
    items_per_job,
):
    array_index = os.getenv("AWS_BATCH_ARRAY_INDEX", 0)
    item_list = [
        *range(array_index * int(items_per_job), (array_index + 1) * int(items_per_job))
    ]
    # Load model.
    if model_uri.startswith("s3"):
        obj = stc.open_file_from_s3(model_uri)["Body"]
        fid_ = io.BufferedReader(obj._raw_stream)
        read_in_memory = fid_.read()
        bio_ = io.BytesIO(read_in_memory)
        f = h5py.File(bio_, "r")
        model = tf.keras.models.load_model(f)
    else:
        model = tf.keras.models.load_model(model_uri)
    # Instanciate generator.
    gen_args = _load_dictionary(generator_config_uri)
    dtgen = stcgen.DataGenerator_stac(collection_uri, **gen_args)
    # Get parent folder for prediciton.
    predict_path = os.path.dirname(generator_config_uri)
    # Predict section (e.g. 500:550)
    for item in item_list:
        out_path = os.path.join(predict_path, "predictions", f"item_{item}")
        meta = dtgen.get_item_metadata(item)
        catalog_id = dtgen.id_list[item]
        x_path = dtgen.catalogs_dict[catalog_id]["x_paths"][0]
        x_path = os.path.join(os.path.dirname(x_path), "stac", "catalog.json")
        if dtgen.expected_x_shape[1:] != model.input_shape[1:]:
            prediction = np.array([])
            data = dtgen[item]
            width = model.input_shape[2]
            height = model.input_shape[3]
            prediction = np.full((width, height), np.nan)
            for i in range(0, dtgen.expected_x_shape[2], width):
                for j in range(0, dtgen.expected_x_shape[2], height):
                    res = data[:, :, i : i + width, j : j + height, :]
                    if res.shape[1:] != model.input_shape[1:]:
                        res = data[:, :, -width:, -height:, :]
                    pred = model.predict(res)
                    # Merge all predicitons
                    pred = pred[0, :, :, :, 0]
                    aux_pred = prediction[i : i + width, j : j + height]
                    mean_pred = np.nanmean([pred, aux_pred], axis=0)
                    prediction[i : i + width, j : j + height] = mean_pred
        else:
            prediction = model.predict(dtgen[item])
            prediction = prediction[0, :, :, :, 0]
        out_path_tif = f"{out_path}.tif"
        _save_and_write_tif(out_path_tif, prediction, meta)
        try:
            it = dtgen.get_items_paths(
                dtgen.collection.get_child(catalog_id), search_for_item=True
            )
            id_raster = os.path.split(out_path_tif)[-1].replace(".tif", "")
            datetime_var = datetime.datetime.now().date()
            footprint = it.geometry
            bbox = it.bbox
            out_meta = meta
            path_item = out_path_tif
            aditional_links = x_path
            href_path = os.path.join(predict_path, "stac", f"{id_raster}_item.json")
            create_pystac_item(
                id_raster,
                footprint,
                bbox,
                datetime_var,
                out_meta,
                path_item,
                aditional_links,
                href_path,
            )
        except Exception as E:
            logger.warning(f"Error in parsing data in predict_function_batch: {E}")
