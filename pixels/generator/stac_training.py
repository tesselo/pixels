import io
import json
import os
import tempfile

import h5py
import numpy as np
import pystac
import structlog
import tensorflow as tf
from rasterio import Affine

from pixels.generator import generator, losses
from pixels.generator.multilabel_confusion_matrix import MultiLabelConfusionMatrix
from pixels.generator.stac_utils import (
    _load_dictionary,
    list_files_in_folder,
    open_file_from_s3,
    upload_files_s3,
    upload_obj_s3,
)
from pixels.utils import NumpyArrayEncoder, write_raster

ALLOWED_CUSTOM_LOSSES = [
    "nan_mean_squared_error_loss",
    "nan_root_mean_squared_error_loss",
    "square_stretching_error_loss",
    "stretching_error_loss",
    "nan_categorical_crossentropy_loss",
    "root_mean_squared_error",
    "nan_categorical_crossentropy_loss_drop_classe",
    "nan_root_mean_squared_error_loss_more_or_less",
]

EVALUATION_PERCENTAGE_LIMIT = 0.2
EVALUATION_SAMPLE_LIMIT = 2000
TRAIN_WITH_ARRAY_LIMIT = 1e7

logger = structlog.get_logger(__name__)


def _save_and_write_tif(out_path, img, meta):
    out_path_tif = out_path
    if out_path.startswith("s3"):
        out_path_tif = out_path_tif.replace("s3://", "tmp/")
    if not os.path.exists(os.path.dirname(out_path_tif)):
        os.makedirs(os.path.dirname(out_path_tif))
    write_raster(img, meta, out_path=out_path_tif, dtype=img.dtype.name)
    if out_path.startswith("s3"):
        upload_files_s3(os.path.dirname(out_path_tif), file_type="tif")


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
        my_str = open_file_from_s3(model_configuration_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        input_config = json.loads(new_str)
        input_config = json.dumps(input_config)
    else:
        # Reading the model from JSON file
        with open(model_configuration_file, "r") as json_file:
            input_config = json_file.read()
    model_j = tf.keras.models.model_from_json(input_config)
    return model_j


def load_existing_model_from_file(
    model_uri, loss="nan_mean_squared_error_loss", loss_arguments={}
):
    # Load model data from S3 if necessary.
    if model_uri.startswith("s3"):
        obj = open_file_from_s3(model_uri)["Body"]
        fid_ = io.BufferedReader(obj._raw_stream)
        read_in_memory = fid_.read()
        bio_ = io.BytesIO(read_in_memory)
        f = h5py.File(bio_, "r")
        model_uri = f
    # Construct model object.
    if hasattr(tf.keras.losses, loss):
        model = tf.keras.models.load_model(model_uri)
    elif loss in ALLOWED_CUSTOM_LOSSES:
        # Handle custome loss functions when loading the model.
        custom_loss = getattr(losses, loss)
        model = tf.keras.models.load_model(
            model_uri,
            custom_objects={"loss": custom_loss(**loss_arguments)},
        )
    else:
        raise ValueError(f"Loss function {loss} is not valid.")

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
                upload_obj_s3(path_model, fl.getvalue())
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
    fit_args = _load_dictionary(model_fit_arguments_uri)
    path_model = os.path.join(os.path.dirname(model_config_uri), "model.h5")
    loss_arguments = compile_args.pop("loss_args", {})
    train_with_array = gen_args.pop("train_with_array", None)
    if gen_args.get("download_data"):
        tmpdir = tempfile.TemporaryDirectory()
        gen_args["download_dir"] = tmpdir.name
    # Check for existing model boolean.
    if compile_args.get("use_existing_model"):
        if "nan_value" in gen_args:
            nan_value = gen_args["nan_value"]
        else:
            nan_value = None
        loss_arguments["nan_value"] = nan_value
        model = load_existing_model_from_file(
            path_model, loss=compile_args["loss"], loss_arguments=loss_arguments
        )
        last_training_epochs = len(
            list_files_in_folder(os.path.dirname(model_config_uri), filetype=".hdf5")
        )
    else:
        last_training_epochs = 0
        # Load model, compile and fit arguments.
        model = load_model_from_file(model_config_uri)
        # Use custom confusion matrix if requested.
        if "MultiLabelConfusionMatrix" in compile_args["metrics"]:
            # Remove string version from metrics.
            compile_args["metrics"].pop(
                compile_args["metrics"].index("MultiLabelConfusionMatrix")
            )
            # Add complied version to metrics.
            compile_args["metrics"].append(
                MultiLabelConfusionMatrix(gen_args.get("num_classes"))
            )
        # Handle custom loss case.
        if hasattr(tf.keras.losses, compile_args["loss"]):
            model.compile(**compile_args)
        elif compile_args["loss"] in ALLOWED_CUSTOM_LOSSES:
            # Get custom loss function.
            custom_loss = getattr(losses, compile_args.pop("loss"))
            # Add nan value to loss arguments.
            loss_arguments["nan_value"] = gen_args.get(
                "nan_value", gen_args.get("y_nan_value", None)
            )
            model.compile(loss=custom_loss(**loss_arguments), **compile_args)
        else:
            raise ValueError(f"Loss function {compile_args['loss']} is not valid.")

    gen_args["dtype"] = model.input.dtype.name
    eval_split = gen_args.pop("eval_split", 0)
    if "training_percentage" not in gen_args:
        gen_args["training_percentage"] = gen_args["split"]
    # Load the class weigths from the Y catalog if requested. Class weights can
    # be passed as a dictionary with the class weights. In this case these
    # will be passed on and not altered. If the class weights key is present,
    # the class weights will be extracted from the Y catalog.
    if "class_weight" in fit_args and fit_args["class_weight"]:
        if isinstance(fit_args["class_weight"], dict):
            class_weight = fit_args["class_weight"]
        else:
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
            class_weight = y_catalog["class_weight"]
        # Ensure class weights have integer keys.
        class_weight = {int(key): val for key, val in class_weight.items()}
        # Remove nodata value from weights if present.
        if gen_args["y_nan_value"] is not None:
            class_weight.pop(gen_args["y_nan_value"], None)
        # Set the class weight fit argument.
        fit_args["class_weight"] = class_weight
    else:
        fit_args["class_weight"] = None
    gen_args["class_weights"] = fit_args["class_weight"]
    # Instanciate generator.
    catalog_path = os.path.join(os.path.dirname(catalog_uri), "catalogs_dict.json")
    gen_args["path_collection_catalog"] = catalog_path
    gen_args["usage_type"] = generator.GENERATOR_MODE_TRAINING
    dtgen = generator.DataGenerator(**gen_args)
    if dtgen.mode in [generator.GENERATOR_3D_MODEL, generator.GENERATOR_2D_MODEL]:
        fit_args.pop("class_weight")

    # Train model, verbose level 2 prints one line per epoch to the log.
    if train_with_array:
        # Stack all items into one array.
        X = []
        Y = []
        pixel_counter = 0
        for x, y in dtgen:
            X.append(x)
            Y.append(y)
            pixel_counter += y.shape[0]
            if pixel_counter > TRAIN_WITH_ARRAY_LIMIT:
                logger.warning(
                    "Training array limit reached, stopping collecting pixels. "
                    f"{pixel_counter} > {TRAIN_WITH_ARRAY_LIMIT}"
                )
                break
        X = np.vstack(X)
        Y = np.vstack(Y)
        # Fit model with data arrays.
        history = model.fit(
            X,
            Y,
            **fit_args,
            callbacks=[
                Custom_Callback_SaveModel_S3(
                    passed_epochs=last_training_epochs,
                    path=os.path.dirname(model_config_uri),
                )
            ],
            verbose=2,
        )
    else:
        # Fit model with generator directly.
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
    # Write history.
    if model_config_uri.startswith("s3"):
        path_ep_md = os.path.dirname(model_config_uri).replace("s3://", "tmp/")
    else:
        path_ep_md = os.path.dirname(model_config_uri)
    if not os.path.exists(path_ep_md):
        os.makedirs(path_ep_md)
    with open(os.path.join(path_ep_md, "history_stats.json"), "w") as f:
        # Get history data.
        hist_data = history.history
        # Write data.
        json.dump(hist_data, f, cls=NumpyArrayEncoder)

    # Store the model in bucket.
    if path_model.startswith("s3"):
        with io.BytesIO() as fl:
            with h5py.File(fl, mode="w") as h5fl:
                model.save(h5fl)
                h5fl.flush()
                h5fl.close()
            upload_obj_s3(path_model, fl.getvalue())
    else:
        with h5py.File(path_model, mode="w") as h5fl:
            model.save(h5fl)

    # Evaluate model on test set.
    gen_args["usage_type"] = generator.GENERATOR_MODE_EVALUATION
    gen_args.pop("class_weights")
    if eval_split == 0:
        gen_args["split"] = 1 - gen_args["split"]
    else:
        gen_args["split"] = eval_split
    if gen_args["split"] <= 0:
        raise ValueError("Negative or 0 split is not allowed.")
    # Limit the evaluation to a maximum of 20% of the dataset.
    if gen_args["split"] > EVALUATION_PERCENTAGE_LIMIT:
        gen_args["split"] = EVALUATION_PERCENTAGE_LIMIT
    # Limit the evaluation to a maximum of 2000 samples.
    if len(dtgen) * gen_args["split"] > EVALUATION_SAMPLE_LIMIT:
        gen_args["split"] = EVALUATION_SAMPLE_LIMIT / len(dtgen)
    if "y_downsample" in gen_args:
        gen_args.pop("y_downsample")
    logger.info(f"Evaluating model on {len(dtgen) * gen_args['split']} samples.")
    dpredgen = generator.DataGenerator(**gen_args)
    results = model.evaluate(dpredgen, verbose=2)
    # Export evaluation statistics to json file.
    with open(os.path.join(path_ep_md, "evaluation_stats.json"), "w") as f:
        json.dump(results, f, cls=NumpyArrayEncoder)
    if model_config_uri.startswith("s3"):
        upload_files_s3(path_ep_md, file_type=".hdf5", delete_folder=False)
        upload_files_s3(path_ep_md, file_type="_stats.json")
    if gen_args.get("download_data"):
        tmpdir.cleanup()
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
    # Load arguments for loss functions and force nan_value from generator.
    loss_arguments = compile_args.pop("loss_args", {})
    if "nan_value" in gen_args:
        nan_value = gen_args["nan_value"]
    else:
        nan_value = None
    loss_arguments["nan_value"] = nan_value
    # Load model.
    model = load_existing_model_from_file(
        model_uri, compile_args["loss"], loss_arguments
    )
    # Instanciate generator, forcing generator to prediction mode.
    gen_args["batch_number"] = 1
    gen_args["usage_type"] = generator.GENERATOR_MODE_PREDICTION
    gen_args["dtype"] = model.input.dtype.name

    # Extract generator arguments that are only for prediction and are not
    # passed to generator. These arguments need to be handled differently in a
    # future implementation. They are not really generator arguments but are
    # passed to this section through the generator arguments dictionary.
    jumping_ratio = gen_args.pop("jumping_ratio", 1)
    jump_pad = gen_args.pop("jump_pad", 0)
    extract_probabilities = gen_args.pop("extract_probabilities", False)
    rescale_probabilities = gen_args.pop("rescale_probabilities", False)

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
        # Get metadata from index, and create paths.
        meta = dtgen.get_meta(item)
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
            prediction = model.predict(data)
            image_shape = (meta["height"], meta["width"], dtgen.num_classes)
            prediction = np.array(prediction.reshape(image_shape))

        # Set the Y nodata value (defaults to none).
        meta["nodata"] = dtgen.y_nan_value

        # Limit the number of bands to be writen in the image file to 1.
        meta["count"] = 1

        # Ensure the class axis is the first one.
        if dtgen.mode == generator.GENERATOR_PIXEL_MODEL:
            prediction = prediction.swapaxes(1, 2)
            prediction = prediction.swapaxes(0, 1)
        else:
            # The probability channels are last, bring them to the front.
            if prediction.shape[-1] == dtgen.num_classes:
                prediction = prediction.swapaxes(2, 3)
                prediction = prediction.swapaxes(1, 2)

        # Issue warning regarding shapes.
        if dtgen.num_classes in (meta["height"], meta["width"]):
            logger.warning(
                "With or height equal to number of classes. "
                "Could not automatically determine column order. "
                "Assuming prediction probability channels last."
            )

        if dtgen.num_classes > 1 and not extract_probabilities:
            # Apply argmax to reduce the one-hot model output into class numbers.
            # Pick axis for argmax calculation based on 1D vs 2D or 3D.
            axis = 0 if dtgen.mode == generator.GENERATOR_PIXEL_MODEL else 1
            prediction = np.argmax(prediction, axis=axis)
            # Ensure the maximum number of classes is not surpassed.
            if np.max(prediction) > 255:
                raise ValueError(
                    f"Model can not have more than 255 classes. Found {np.max(prediction)}."
                )
            # Rasterio expects shape to have the band number first. So expand
            # prediction shape from (height, width) to (1, height, width).
            if dtgen.mode == generator.GENERATOR_PIXEL_MODEL:
                prediction = prediction.reshape(*(1, *prediction.shape))
            # Ensure prediction has a writable type. For now, we assume there
            # will not be more than 255 classes and use unit8. The default
            # argmax type is Int64 which is not a valid format for gdal.
            prediction = prediction.astype("uint8")
            meta["dtype"] = "uint8"

        # If requested, rescale the probabilities to integers from 0 to 255.
        # This keeps a reasonable precision and reduces the data size
        # substancially.
        if rescale_probabilities and (dtgen.num_classes == 1 or extract_probabilities):
            prediction = np.rint(prediction * 255).astype("uint8")
            # Override the nodata value and the datatype.
            meta["nodata"] = None
            meta["dtype"] = "uint8"

        # Conditions to be met when the probablities are to be extracted.
        if extract_probabilities:
            # When probabilities are to be extracted the number of bands is the number of classes.
            meta["count"] = dtgen.num_classes
            if dtgen.mode == generator.GENERATOR_PIXEL_MODEL:
                prediction = prediction.reshape(*(1, *prediction.shape))

        # Compute target resolution using upscale factor.
        meta["transform"] = Affine(
            meta["transform"][0] / dtgen.upsampling,
            meta["transform"][1],
            meta["transform"][2],
            meta["transform"][3],
            meta["transform"][4] / dtgen.upsampling,
            meta["transform"][5],
        )

        # Prepare output path for this item, using the catalog_id in the file
        # name to match the ID from the collection.
        catalog_id = dtgen.id_list[item]
        out_path = os.path.join(predict_path, "predictions", f"item_{catalog_id}")

        # Write the prediction data to files.
        if len(prediction) == 1:
            _save_and_write_tif(f"{out_path}.tif", prediction[0], meta)
        else:
            # Compute date list for the multiple images input for naming the
            # output files.
            date_list = dtgen.collection_catalog[catalog_id]["x_paths"]
            date_list = [
                os.path.basename(date).replace(".tif", "") for date in date_list
            ][: dtgen.timesteps]
            # For each input image, write one output prediction file with the
            # date stamp in the name.
            for index, prediction_data in enumerate(prediction):
                _save_and_write_tif(
                    f"{out_path}_{date_list[index]}.tif", prediction_data, meta
                )
