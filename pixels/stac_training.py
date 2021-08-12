import datetime
import io
import json
import os

import h5py
import numpy as np
import pystac
import sentry_sdk
import structlog
import tensorflow as tf
import tensorflow_addons
from dateutil import parser
from rasterio import Affine

import pixels.stac as stc
from pixels import losses
from pixels.generator import generator
from pixels.stac_utils import _load_dictionary
from pixels.utils import write_raster

ALLOWED_CUSTOM_LOSSES = [
    "nan_mean_squared_error_loss",
    "nan_root_mean_squared_error_loss",
    "square_stretching_error_loss",
    "stretching_error_loss",
    "nan_categorical_crossentropy_loss",
]

logger = structlog.get_logger(__name__)


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


def get_custom_loss(compile_args):
    if not hasattr(tf.keras.losses, compile_args["loss"]):
        input = compile_args["loss"]
        # Validate input
        if input not in ALLOWED_CUSTOM_LOSSES:
            raise ValueError()
        loss_custom = getattr(losses, input)
        if not loss_custom:
            logger.warning(
                f"Method {compile_args['loss']} not implemented, going for mse."
            )
            loss_custom = tf.keras.losses.mean_squared_error
        compile_args.pop("loss")
    return loss_custom


def load_existing_model_from_file(
    model_uri, loss_dict={"loss": "nan_mean_squared_error_loss"}, nan_value=-9999
):
    # Load model.
    if model_uri.startswith("s3"):
        obj = stc.open_file_from_s3(model_uri)["Body"]
        fid_ = io.BufferedReader(obj._raw_stream)
        read_in_memory = fid_.read()
        bio_ = io.BytesIO(read_in_memory)
        f = h5py.File(bio_, "r")
        model_uri = f
    try:
        model = tf.keras.models.load_model(model_uri)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        model = tf.keras.models.load_model(
            model_uri, custom_objects={"loss": get_custom_loss(loss_dict)(nan_value)}
        )
    return model


class Custom_Callback_SaveModel_S3(tf.keras.callbacks.Callback):
    """
    Custom Callback function to save and upload to s3 models on epoch end.

    Parameters
    ----------
        passed_epochs : int
            Number of epochs already trained on the model.
        path : string
            Path to model folder.
    """

    def __init__(self, passed_epochs, path):
        self.passed_epochs = passed_epochs
        self.path = path

    def on_epoch_end(self, epoch, logs=None):
        epoch_number = epoch + self.passed_epochs + 1
        path_model = os.path.join(self.path, f"model_epoch_{epoch_number}.hdf5")
        # Store the model in bucket.
        if path_model.startswith("s3"):
            with io.BytesIO() as fl:
                with h5py.File(fl, mode="w") as h5fl:
                    self.model.save(h5fl)
                    h5fl.flush()
                    h5fl.close()
                stc.upload_obj_s3(path_model, fl.getvalue())
        else:
            with h5py.File(path_model, mode="w") as h5fl:
                self.model.save(h5fl)


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
    compile_args = _load_dictionary(model_compile_arguments_uri)
    path_model = os.path.join(os.path.dirname(model_config_uri), "model.h5")
    # Check for existing model boolean.
    if "use_existing_model" in compile_args:
        if compile_args["use_existing_model"]:
            no_compile = True
            if "nan_value" in gen_args:
                nan_value = gen_args["nan_value"]
            else:
                nan_value = None
            model = load_existing_model_from_file(
                path_model, loss_dict=compile_args, nan_value=nan_value
            )
            last_training_epochs = len(
                stc.list_files_in_folder(
                    os.path.dirname(model_config_uri), filetype=".hdf5"
                )
            )
            logger.warning(
                f"Training from existing model with {last_training_epochs} trained epochs."
            )
    else:
        no_compile = False
        last_training_epochs = 0
        # Load model, compile and fit arguments.
        model = load_model_from_file(model_config_uri)

    gen_args["dtype"] = model.input.dtype.name
    eval_split = gen_args.pop("eval_split", 0)
    if "training_percentage" not in gen_args:
        gen_args["training_percentage"] = gen_args["split"]
    # Instanciate generator.
    catalog_path = os.path.join(os.path.dirname(catalog_uri), "catalogs_dict.json")
    gen_args["path_collection_catalog"] = catalog_path
    gen_args["usage_type"] = generator.GENERATOR_MODE_TRAINING
    dtgen = generator.DataGenerator(**gen_args)
    if not no_compile:
        # Compile confusion matrix if requested.
        if "MultiLabelConfusionMatrix" in compile_args["metrics"]:
            # Remove string version from metrics.
            compile_args["metrics"].pop(
                compile_args["metrics"].index("MultiLabelConfusionMatrix")
            )
            # Add complied version to metrics.
            compile_args["metrics"].append(
                tensorflow_addons.metrics.MultiLabelConfusionMatrix(
                    num_classes=dtgen.num_classes
                )
            )

        # Handle custom loss case.
        if not hasattr(tf.keras.losses, compile_args["loss"]):
            input = compile_args["loss"]
            # Validate input
            if input not in ALLOWED_CUSTOM_LOSSES:
                raise ValueError()
            loss_costum = getattr(losses, input)
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
    # Train model.
    # Load the class weigths from the Y catalog if requested. Class weights can
    # be passed as a dictionary with the class weights. In this case these
    # will be passed on and not altered. If the class weights key is present,
    # the class weights will be extracted from the Y catalog.
    if (
        "class_weight" in fit_args
        and fit_args["class_weight"]
        and not isinstance(fit_args["class_weight"], dict)
    ):
        # Open x catalog.
        x_catalog = _load_dictionary(catalog_uri)
        # Get origin files zip link from dictonary.
        origin_files = [
            dat for dat in x_catalog["links"] if dat["rel"] == "origin_files"
        ][0]["href"]
        # Construct y catalog uri.
        y_catalog_uri = os.path.join(
            os.path.dirname(origin_files), "stac", "catalog.json"
        )
        # Open y catalog.
        y_catalog = _load_dictionary(str(y_catalog_uri))
        # Get stats from y catalog.
        if "class_weight" in y_catalog:
            # Ensure class weights have integer keys.
            class_weight = {
                int(key): val for key, val in y_catalog["class_weight"].items()
            }
            # Remove nodata value from weights if present.
            if dtgen.y_nan_value is not None:
                class_weight.pop(dtgen.y_nan_value, None)
            # Set the class weight fit argument.
            fit_args["class_weight"] = class_weight
        else:
            fit_args["class_weight"] = None
    # Verbose level 2 prints one line per epoch to the log.
    history = model.fit(
        dtgen,
        **fit_args,
        callbacks=[
            Custom_Callback_SaveModel_S3(
                passed_epochs=last_training_epochs,
                path=os.path.dirname(model_config_uri),
            )
        ],
        verbose=2,
    )
    with open(os.path.join(path_ep_md, "history_stats.json"), "w") as f:
        # Get history data.
        hist_data = history.history
        # Convert confusion matrix elements in history from numpy array to
        # lists. This is to ensure json serializability.
        if "Multilabel_confusion_matrix" in hist_data:
            hist_data["Multilabel_confusion_matrix"] = [
                dat.tolist() for dat in hist_data["Multilabel_confusion_matrix"]
            ]
        # Write data.
        json.dump(hist_data, f)

    # Store the model in bucket.
    if path_model.startswith("s3"):
        with io.BytesIO() as fl:
            with h5py.File(fl, mode="w") as h5fl:
                model.save(h5fl)
                h5fl.flush()
                h5fl.close()
            stc.upload_obj_s3(path_model, fl.getvalue())
    else:
        with h5py.File(path_model, mode="w") as h5fl:
            model.save(h5fl)

    # Evaluate model on test set.
    gen_args["usage_type"] = generator.GENERATOR_MODE_EVALUATION
    if eval_split == 0:
        gen_args["split"] = 1 - gen_args["split"]
    else:
        gen_args["split"] = eval_split
    if gen_args["split"] <= 0:
        raise ValueError("Negative or 0 split is not allowed.")
    if "y_downsample" in gen_args:
        gen_args.pop("y_downsample")
    logger.info(f"Evaluating model on {len(dtgen) * gen_args['split']} samples.")
    dpredgen = generator.DataGenerator(**gen_args)
    results = model.evaluate(dpredgen, verbose=2)
    with open(os.path.join(path_ep_md, "evaluation_stats.json"), "w") as f:
        json.dump(results, f)
    if model_config_uri.startswith("s3"):
        stc.upload_files_s3(path_ep_md, file_type=".hdf5", delete_folder=False)
        stc.upload_files_s3(path_ep_md, file_type="_stats.json")

    # Save collection index dictionary.
    catalog_dict_path = os.path.join(os.path.dirname(catalog_uri), "catalogs_dict.json")
    catalog_dict = dtgen.collection_catalog
    catalog_dict.update(dpredgen.collection_catalog)
    if catalog_dict_path.startswith("s3"):
        catalog_dict_path = catalog_dict_path.replace("s3://", "tmp/")
    if not os.path.exists(catalog_dict_path):
        try:
            os.makedirs(os.path.dirname(catalog_dict_path))
        except OSError:
            # Directory already exists.
            pass
    with open(catalog_dict_path, "w") as f:
        json.dump(catalog_dict, f)
    if catalog_uri.startswith("s3"):
        stc.upload_files_s3(
            os.path.dirname(catalog_dict_path),
            file_type="_dict.json",
            delete_folder=False,
        )

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
    gen_args = _load_dictionary(generator_config_uri)
    compile_args = _load_dictionary(
        os.path.join(os.path.dirname(model_uri), "compile_arguments.json")
    )
    # Get loss function.
    if "loss" in compile_args:
        if not hasattr(tf.keras.losses, compile_args["loss"]):
            input = compile_args["loss"]
            # Validate input
            if input not in ALLOWED_CUSTOM_LOSSES:
                raise ValueError()
            loss_costum = getattr(losses, input)
            if not loss_costum:
                logger.warning(f"Method {input} not implemented, going for mse.")
                loss_costum = tf.keras.losses.mean_squared_error
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
        except Exception as e:
            sentry_sdk.capture_exception(e)
            model = tf.keras.models.load_model(
                f, custom_objects={"loss": loss_costum(gen_args["nan_value"])}
            )
    else:
        try:
            model = tf.keras.models.load_model(model_uri)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            model = tf.keras.models.load_model(
                model_uri, custom_objects={"loss": loss_costum(gen_args["nan_value"])}
            )
    # Instanciate generator.
    # Force generator to prediction.
    gen_args["batch_number"] = 1
    gen_args["usage_type"] = generator.GENERATOR_MODE_PREDICTION
    gen_args["dtype"] = model.input.dtype.name
    if "jumping_ratio" not in gen_args:
        jumping_ratio = 1
    else:
        jumping_ratio = gen_args["jumping_ratio"]
        gen_args.pop("jumping_ratio")
    if "jump_pad" not in gen_args:
        jump_pad = 0
    else:
        jump_pad = gen_args["jump_pad"]
        gen_args.pop("jump_pad")

    catalog_path = os.path.join(os.path.dirname(collection_uri), "catalogs_dict.json")
    gen_args["path_collection_catalog"] = catalog_path
    dtgen = generator.DataGenerator(**gen_args)
    # Get parent folder for prediciton.
    predict_path = os.path.dirname(generator_config_uri)
    # Get jobs array.
    array_index = int(os.getenv("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    item_list_max = (array_index + 1) * int(items_per_job)
    if item_list_max > len(dtgen):
        item_list_max = len(dtgen)
    item_list_min = array_index * int(items_per_job)
    item_range = range(item_list_min, item_list_max)
    logger.info(f"Predicting generator range from {item_list_min} to {item_list_max}.")
    # Predict the index range for this batch job.
    for item in item_range:
        out_path = os.path.join(predict_path, "predictions", f"item_{item}")
        # Get metadata from index, and create paths.
        meta = dtgen.get_meta(item)
        catalog_id = dtgen.id_list[item]
        x_path = dtgen.collection_catalog[catalog_id]["x_paths"][0]
        date_list = dtgen.collection_catalog[catalog_id]["x_paths"]
        date_list = [os.path.basename(date).replace(".tif", "") for date in date_list][
            : dtgen.timesteps
        ]
        x_path = os.path.join(os.path.dirname(x_path), "stac", "catalog.json")
        if dtgen.mode in [generator.GENERATOR_3D_MODEL, generator.GENERATOR_2D_MODEL]:
            # Index img number based on mode.
            if dtgen.mode == generator.GENERATOR_3D_MODEL:
                width_index = 3
                height_index = 2
            else:
                width_index = 2
                height_index = 1
            # If the generator output is bigger than model shape, do a jumping window.
            big_square_width = dtgen.expected_x_shape[width_index]
            big_square_height = dtgen.expected_x_shape[height_index]
            big_square_width_result = big_square_width - (dtgen.padding * 2)
            big_square_height_result = big_square_height - (dtgen.padding * 2)
            # Moving window for prediction with bigger shapes than model.
            if dtgen.expected_x_shape[1:] != model.input_shape[1:]:
                logger.warning(
                    f"Shapes from Input data are different from model. Input:{dtgen.expected_x_shape[1:]}, model:{model.input_shape[1:]}."
                )
                # Get the data (X).
                data = dtgen[item]
                # 3D model shape: (N, T, h, w, b)
                # 2D model shape: (N, h, w, b)
                # In order to keep the same structure for both cases
                # we make the 2D mode like a case of 3D with 1 timestep.
                # For that we create a dimension.
                if len(data.shape) < 5:
                    data = np.expand_dims(data, axis=1)
                num_imgs = len(data)
                width = model.input_shape[width_index]
                height = model.input_shape[height_index]
                jumping_width = width - (dtgen.padding * 2)
                jumping_height = height - (dtgen.padding * 2)
                jump_width = int(jumping_width * jumping_ratio)
                jump_height = int(jumping_height * jumping_ratio)
                # Instanciate empty result matrix.
                prediction = np.full(
                    (
                        num_imgs,
                        big_square_width_result,
                        big_square_height_result,
                        dtgen.num_classes,
                    ),
                    np.nan,
                )
                pred_num_it = np.zeros(prediction.shape)
                # Create a jumping window with the expected size.
                # For every window replace the values in the result matrix.
                for i in range(0, big_square_width, jump_width):
                    for j in range(0, big_square_height, jump_height):
                        res = data[:, :, j : j + height, i : i + width, :]
                        if res.shape[1:] != model.input_shape[1:]:
                            if big_square_height - j < height:
                                res = data[:, :, -height:, i : i + width, :]
                            if big_square_width - i < width:
                                res = data[:, :, j : j + height, -width:, :]
                            if (
                                big_square_height - j < height
                                and big_square_width - i < width
                            ):
                                res = data[:, :, -height:, -width:, :]
                        # If 2D mode break aditional dimension.
                        if dtgen.mode == generator.GENERATOR_2D_MODEL:
                            res = res[:, 0]
                        pred = model.predict(res)
                        # Merge all predicitons
                        jump_pad_j_i = jump_pad
                        jump_pad_j_f = jump_pad
                        jump_pad_i_i = jump_pad
                        jump_pad_i_f = jump_pad
                        if i == 0:
                            jump_pad_i_i = 0
                        if big_square_width - i < jump_width:
                            jump_pad_i_f = 0
                        if j == 0:
                            jump_pad_j_i = 0
                        if big_square_height - j < jump_height:
                            jump_pad_j_f = 0
                        # Get only the array without the padding.
                        pred = pred[
                            :,
                            jump_pad_j_i : pred.shape[1] - jump_pad_j_f,
                            jump_pad_i_i : pred.shape[2] - jump_pad_i_f,
                            :,
                        ]
                        # Get the image from the main prediction.
                        aux_pred = prediction[
                            :,
                            j + jump_pad_j_i : j + jumping_height - jump_pad_j_f,
                            i + jump_pad_i_i : i + jumping_width - jump_pad_i_f,
                            :,
                        ]
                        if aux_pred.shape != pred.shape:
                            pred = pred[
                                pred.shape[0] - aux_pred.shape[0] :,
                                pred.shape[1] - aux_pred.shape[1] :,
                                pred.shape[2] - aux_pred.shape[2] :,
                                pred.shape[3] - aux_pred.shape[3] :,
                            ]
                        aux_sum = pred_num_it[
                            :,
                            j + jump_pad_j_i : j + jumping_height - jump_pad_j_f,
                            i + jump_pad_i_i : i + jumping_width - jump_pad_i_f,
                            :,
                        ]
                        pred_sum = np.ones(pred.shape)
                        # Summed the new pixel with the old.
                        summed_pred = np.nansum([pred, aux_pred], axis=0)
                        prediction[
                            :,
                            j + jump_pad_j_i : j + jumping_height - jump_pad_j_f,
                            i + jump_pad_i_i : i + jumping_width - jump_pad_i_f,
                        ] = summed_pred
                        # Summed secction of iteration on each pixel.
                        summed_iteration = np.sum([aux_sum, pred_sum], axis=0)
                        pred_num_it[
                            :,
                            j + jump_pad_j_i : j + jumping_height - jump_pad_j_f,
                            i + jump_pad_i_i : i + jumping_width - jump_pad_i_f,
                        ] = summed_iteration
                prediction[prediction != prediction] = dtgen.nan_value
                pred_num_it[pred_num_it == 0] = 1
                # Mean of all prediction based on pixel iteration.
                prediction = prediction / pred_num_it
            else:
                prediction = model.predict(dtgen[item])
            meta["width"] = big_square_width_result
            meta["height"] = big_square_height_result

        if dtgen.mode == generator.GENERATOR_PIXEL_MODEL:
            data = dtgen[item]
            # for pixel in data:
            prediction = model.predict(data)
            image_shape = (meta["height"], meta["width"], dtgen.num_classes)
            # Check for nan values. TODO.
            prediction = np.array[prediction.reshape(image_shape)]

        # Fix number of bands to 1. This assumes multiclass output always is
        # converted to a single band with the class numbers.
        meta["count"] = 1

        # Set the Y nodata value (defaults to none).
        meta["nodata"] = dtgen.y_nan_value
        # Ensure the class axis is the first one.
        prediction = prediction.swapaxes(2, 3)
        prediction = prediction.swapaxes(1, 2)

        # Apply argmax to reduce the one-hot model output into class numbers.
        if dtgen.num_classes > 1:
            prediction = np.argmax(prediction, axis=1)
            # Ensure prediction has a writable type. For now, we assume there
            # will not be more than 255 classes and use unit8. The default
            # argmax type is Int64 which is not a valid format for gdal.
            prediction = prediction.astype("uint8")

        # Compute target resolution using upscale factor.
        meta["transform"] = Affine(
            meta["transform"][0] / dtgen.upsampling,
            meta["transform"][1],
            meta["transform"][2],
            meta["transform"][3],
            meta["transform"][4] / dtgen.upsampling,
            meta["transform"][5],
        )
        # Save the prediction tif.
        if len(prediction) == 1:
            out_path_tif = f"{out_path}.tif"
            _save_and_write_tif(out_path_tif, prediction[0], meta)
        else:
            # Save multiple prediction images.
            for image_count in range(len(prediction)):
                out_path_tif = f"{out_path}_{date_list[image_count]}.tif"
                _save_and_write_tif(out_path_tif, prediction[image_count], meta)
                image_count = image_count + 1
        # Build the corresponding pystac item.
        try:
            cat = pystac.Catalog.from_file(
                dtgen.collection_catalog[catalog_id]["stac_catalog"]
            )
            for itt in cat.get_items():
                it = itt
                break
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
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.warning(f"Error in parsing data in predict_function_batch: {e}")
