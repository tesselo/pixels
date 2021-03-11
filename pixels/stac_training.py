import ast
import datetime
import io
import json
import logging
import os

import h5py
import numpy as np
import pystac
import tensorflow as tf
from dateutil import parser
from rasterio import Affine

import pixels.stac as stc
import pixels.stac_generator.generator_class as stcgen
from pixels.utils import write_raster

logger = logging.getLogger(__name__)


def _load_dictionary(path_file):
    # Open config file and load as dict.
    if path_file.startswith("s3"):
        my_str = stc.open_file_from_s3(path_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        dicti = json.loads(new_str)
    else:
        with open(path_file, "r") as json_file:
            input_config = json_file.read()
            dicti = ast.literal_eval(input_config)
    return dicti


def _save_and_write_tif(out_path, img, meta):
    out_path_tif = out_path
    if out_path.startswith("s3"):
        out_path_tif = out_path_tif.replace("s3://", "tmp/")
    if not os.path.exists(os.path.dirname(out_path_tif)):
        os.makedirs(os.path.dirname(out_path_tif))
    write_raster(img, meta, out_path=out_path_tif, dtype=img.dtype.name)
    if out_path.startswith("s3"):
        stc.upload_files_s3(os.path.dirname(out_path_tif), file_type="tif")


def create_pystac_item(
    id_raster,
    footprint,
    bbox,
    datetime_var,
    meta,
    path_item,
    aditional_links,
    href_path,
):
    out_meta = {}
    # Add projection stac extension, assuming input crs has a EPSG id.
    out_meta["proj:epsg"] = meta["crs"].to_epsg()
    out_meta["stac_extensions"] = ["projection"]
    # Make transform and crs json serializable.
    out_meta["crs"] = {"init": "epsg:" + str(meta["crs"].to_epsg())}
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
        if isinstance(aditional_links, dict):
            for key in aditional_links.keys():
                item.add_link(pystac.Link(key, aditional_links[key]))
        else:
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


def nan_mean_squared_error_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        if y_true.shape != y_pred.shape:
            y_true = y_true[:, :1]
        indices = tf.where(tf.not_equal(y_true, nan_value))
        return tf.keras.losses.mean_squared_error(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


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
    # Load the generator arguments.
    gen_args = _load_dictionary(generator_arguments_uri)
    # Instanciate generator.
    dtgen = stcgen.DataGenerator_stac(catalog_uri, **gen_args)
    # Load model, compile and fit arguments.
    model = load_model_from_file(model_config_uri)
    compile_args = _load_dictionary(model_compile_arguments_uri)
    if not hasattr(tf.keras.losses, compile_args["loss"]):
        possibles = globals().copy()
        possibles.update(locals())
        loss_costum = possibles.get(compile_args["loss"])
        loss_args = {"nan_value": dtgen.nan_value}
        if not loss_costum:
            logger.warning(
                f"Method {compile_args['loss']} not implemented, going for mse."
            )
            loss_costum = tf.keras.losses.mean_squared_error
            loss_args = {}
        compile_args.pop("loss")
        model.compile(loss=loss_costum(**loss_args), **compile_args)
    else:
        model.compile(**compile_args)
    fit_args = _load_dictionary(model_fit_arguments_uri)
    if model_config_uri.startswith("s3"):
        path_ep_md = os.path.dirname(model_config_uri).replace("s3://", "tmp/")
    else:
        path_ep_md = os.path.dirname(model_config_uri)
    if not os.path.exists(path_ep_md):
        os.makedirs(path_ep_md)
    path_model = os.path.join(os.path.dirname(model_config_uri), "model.h5")
    # Train model.
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        os.path.join(path_ep_md, "model_{epoch:02d}.hdf5"),
        monitor="loss",
        verbose=1,
        save_best_only=False,
        mode="auto",
        save_freq="epoch",
    )
    # Verbose level 2 prints one line per epoch to the log.
    history = model.fit(dtgen, **fit_args, callbacks=[checkpoint], verbose=2)
    with open(os.path.join(path_ep_md, "history.json"), "w") as f:
        json.dump(history.history, f)
    if model_config_uri.startswith("s3"):
        stc.upload_files_s3(path_ep_md, file_type=".hdf5")
        stc.upload_files_s3(path_ep_md, file_type="tory.json")

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
    collection_uri,
    generator_config_uri,
    items_per_job,
):
    """
    From a trained model and the cnfigurations files build the predictions on
    the given data. Save the predictions and pystac items representing them.

    Parameters
    ----------
        model_uri : keras model h5
            Trained model.
        generator_config_uri : path to json file
            File of dictonary containing the generator configuration.
        collection_uri : str, path
            Collection with the information from the input data.
        items_per_job : int
            Number of items per jobs.
    """
    # Load model.
    if model_uri.startswith("s3"):
        obj = stc.open_file_from_s3(model_uri)["Body"]
        fid_ = io.BufferedReader(obj._raw_stream)
        read_in_memory = fid_.read()
        bio_ = io.BytesIO(read_in_memory)
        f = h5py.File(bio_, "r")
        # TODO: Change this!
        try:
            model = tf.keras.models.load_model(f)
        except:
            model = tf.keras.models.load_model(
                f, custom_objects={"loss": nan_mean_squared_error_loss}
            )
    else:
        try:
            model = tf.keras.models.load_model(model_uri)
        except:
            model = tf.keras.models.load_model(
                model_uri, custom_objects={"loss": nan_mean_squared_error_loss}
            )
    # Instanciate generator.
    gen_args = _load_dictionary(generator_config_uri)
    # Force generator to prediction.
    gen_args["train"] = False
    dtgen = stcgen.DataGenerator_stac(collection_uri, **gen_args)
    # Get parent folder for prediciton.
    predict_path = os.path.dirname(generator_config_uri)
    # Get jobs array.
    array_index = os.getenv("AWS_BATCH_ARRAY_INDEX", 0)
    item_list_max = (array_index + 1) * int(items_per_job)
    if item_list_max > len(dtgen):
        item_list_max = len(dtgen)
    item_list = [*range(array_index * int(items_per_job), item_list_max)]
    # Predict section (e.g. 500:550).
    # Predict for every item (index).
    for item in item_list:
        out_path = os.path.join(predict_path, "predictions", f"item_{item}")
        # Get metadata from index, and create paths.
        meta = dtgen.get_item_metadata(item)
        catalog_id = dtgen.id_list[item]
        x_path = dtgen.catalogs_dict[catalog_id]["x_paths"][0]
        x_path = os.path.join(os.path.dirname(x_path), "stac", "catalog.json")
        # If the generator output is bigger than model shape, do a jumping window.
        if dtgen.expected_x_shape[1:] != model.input_shape[1:]:
            # Get the data (X).
            data = dtgen[item]
            width = model.input_shape[2]
            height = model.input_shape[3]
            # Instanciate empty result matrix.
            prediction = np.full((width, height), np.nan)
            # Create a jumping window with the expected size.
            # For every window replace the values in the result matrix.
            for i in range(0, dtgen.expected_x_shape[2], width):
                for j in range(0, dtgen.expected_x_shape[3], height):
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
            # out_path_temp = out_path.replace("s3://", "tmp/")
            # if not os.path.exists(os.path.dirname(out_path_temp)):
            #     os.makedirs(os.path.dirname(out_path_temp))
            # np.savez(f"{out_path_temp}.npz", prediction)
            # stc.upload_files_s3(os.path.dirname(out_path_temp), file_type='.npz')
            prediction = prediction[0, :, :, :, 0]
        # TODO: verify input shape with rasterio
        meta["width"] = model.input_shape[2]
        meta["height"] = model.input_shape[3]
        meta["count"] = 1
        # Compute target resolution using upscale factor.
        meta["transform"] = Affine(
            meta["transform"][0] / gen_args["upsampling"],
            meta["transform"][1],
            meta["transform"][2],
            meta["transform"][3],
            meta["transform"][4] / gen_args["upsampling"],
            meta["transform"][5],
        )
        # Save the prediction tif.
        out_path_tif = f"{out_path}.tif"
        _save_and_write_tif(out_path_tif, prediction, meta)
        # Build the corresponding pystac item.
        try:
            it = dtgen.get_items_paths(
                dtgen.collection.get_child(catalog_id), search_for_item=True
            )
            # id_raster = os.path.split(out_path_tif)[-1].replace(".tif", "")
            id_raster = catalog_id
            datetime_var = str(datetime.datetime.now().date())
            datetime_var = parser.parse(datetime_var)
            footprint = it.geometry
            bbox = it.bbox
            path_item = out_path_tif
            aditional_links = {"x_catalog": x_path, "model_used": model_uri}
            href_path = os.path.join(predict_path, "stac", f"{id_raster}_item.json")
            create_pystac_item(
                id_raster,
                footprint,
                bbox,
                datetime_var,
                meta,
                path_item,
                aditional_links,
                href_path,
            )
        except Exception as E:
            logger.warning(f"Error in parsing data in predict_function_batch: {E}")


def predict_function(
    model_uri,
    collection_uri,
    generator_config_uri,
):
    """
    From a trained model and the cnfigurations files build the predictions on
    the given data. Save the predictions and pystac items representing them.

    Parameters
    ----------
        model_uri : keras model h5
            Trained model.
        generator_config_uri : path to json file
            File of dictonary containing the generator configuration.
        collection_uri : str, path
            Collection with the information from the input data.
    """
    # Load model.
    if model_uri.startswith("s3"):
        obj = stc.open_file_from_s3(model_uri)["Body"]
        fid_ = io.BufferedReader(obj._raw_stream)
        read_in_memory = fid_.read()
        bio_ = io.BytesIO(read_in_memory)
        f = h5py.File(bio_, "r")
        # TODO: hardcoded custom loss function.
        try:
            model = tf.keras.models.load_model(f)
        except:
            model = tf.keras.models.load_model(
                f, custom_objects={"loss": nan_mean_squared_error_loss}
            )
    else:
        try:
            model = tf.keras.models.load_model(model_uri)
        except:
            model = tf.keras.models.load_model(
                model_uri, custom_objects={"loss": nan_mean_squared_error_loss}
            )
    # Instanciate generator.
    gen_args = _load_dictionary(generator_config_uri)
    # Force generator to prediction.
    gen_args["train"] = False
    dtgen = stcgen.DataGenerator_stac(collection_uri, **gen_args)
    # Get parent folder for prediciton.
    predict_path = os.path.dirname(generator_config_uri)
    # Predict section (e.g. 500:550).
    # Predict for every item (index).
    for item in range(len(dtgen)):
        out_path = os.path.join(predict_path, "predictions", f"item_{item}")
        # Get metadata from index, and create paths.
        meta = dtgen.get_item_metadata(item)
        catalog_id = dtgen.id_list[item]
        x_path = dtgen.catalogs_dict[catalog_id]["x_paths"][0]
        x_path = os.path.join(os.path.dirname(x_path), "stac", "catalog.json")
        # If the generator output is bigger than model shape, do a jumping window.
        if dtgen.expected_x_shape[1:] != model.input_shape[1:]:
            # Get the data (X).
            data = dtgen[item]
            width = model.input_shape[2]
            height = model.input_shape[3]
            # Instanciate empty result matrix.
            prediction = np.full((width, height), np.nan)
            # Create a jumping window with the expected size.
            # For every window replace the values in the result matrix.
            for i in range(0, dtgen.expected_x_shape[2], width):
                for j in range(0, dtgen.expected_x_shape[3], height):
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
            # out_path_temp = out_path.replace("s3://", "tmp/")
            # if not os.path.exists(os.path.dirname(out_path_temp)):
            #     os.makedirs(os.path.dirname(out_path_temp))
            # np.savez(f"{out_path_temp}.npz", prediction)
            # stc.upload_files_s3(os.path.dirname(out_path_temp), file_type='.npz')
            prediction = prediction[0, :, :, :, 0]
        # TODO: verify input shape with rasterio
        meta["width"] = model.input_shape[2]
        meta["height"] = model.input_shape[3]
        meta["count"] = 1
        meta["transform"] = Affine(
            1,
            meta["transform"][1],
            meta["transform"][2],
            meta["transform"][3],
            -1,
            meta["transform"][5],
        )
        # Save the prediction tif.
        out_path_tif = f"{out_path}.tif"
        _save_and_write_tif(out_path_tif, prediction, meta)
        # Build the corresponding pystac item.
        try:
            it = dtgen.get_items_paths(
                dtgen.collection.get_child(catalog_id), search_for_item=True
            )
            # id_raster = os.path.split(out_path_tif)[-1].replace(".tif", "")
            id_raster = catalog_id
            datetime_var = str(datetime.datetime.now().date())
            datetime_var = parser.parse(datetime_var)
            footprint = it.geometry
            bbox = it.bbox
            path_item = out_path_tif
            aditional_links = {"x_catalog": x_path, "model_used": model_uri}
            href_path = os.path.join(predict_path, "stac", f"{id_raster}_item.json")
            create_pystac_item(
                id_raster,
                footprint,
                bbox,
                datetime_var,
                meta,
                path_item,
                aditional_links,
                href_path,
            )
        except Exception as E:
            logger.warning(f"Error in parsing data in predict_function_batch: {E}")
