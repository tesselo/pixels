import json
import os
import tempfile
from io import BufferedReader, BytesIO

import h5py
import numpy as np
import pystac
import tensorflow as tf
import tensorflow_addons as tfa
from rasterio import Affine

from pixels import tio
from pixels.const import ALLOWED_CUSTOM_LOSSES, NAN_VALUE_LOSSES, TRAIN_WITH_ARRAY_LIMIT
from pixels.generator import generator, losses
from pixels.generator.validators import GeneratorArgumentsValidator
from pixels.log import log_function, logger
from pixels.slack import SlackClient
from pixels.stac.utils import plot_history
from pixels.tio.virtual import model_uri
from pixels.utils import NumpyArrayEncoder

MODE_PREDICTION_PER_PIXEL = [
    generator.GENERATOR_PIXEL_MODEL,
    *generator.GENERATOR_RESNET_MODES,
]
MODE_PREDICTION_PER_IMAGE = generator.GENERATOR_UNET_MODEL


def _save_and_write_tif(uri, img, meta):
    out_path = tio.local_or_temp(uri)
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)
    tio.write_raster(img, meta, out_path=out_path, dtype=img.dtype.name)
    if tio.is_remote(uri):
        tio.upload(out_dir, suffix=".tif")


def create_pystac_item(
    id_raster,
    footprint,
    bbox,
    datetime_var,
    meta,
    path_item,
    additional_links,
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
    if additional_links:
        if isinstance(additional_links, dict):
            for key in additional_links.keys():
                item.add_link(pystac.Link(key, additional_links[key]))
        else:
            item.add_link(pystac.Link("x_catalog", additional_links))
    item.set_self_href(href_path)
    # Validate item.
    item.validate()
    item.save_object()
    return item


def load_model(model_path):
    input_config = tio.load_dictionary(model_path)
    return tf.keras.models.model_from_config(input_config)


def load_loss_function(loss, loss_arguments):
    """
    Loads the loss function to use in training.

    Parameters
    ----------
        loss : str
            Name of the loss function to use.
        loss_arguments : dict
            Arguments for the loss function.
    Returns
    -------
        loss_function : function
            Loss function to use in training.
    """
    nan_value = loss_arguments.pop("nan_value", None)

    # Handle custom loss case.
    if hasattr(tf.keras.losses, loss):
        loss_function = getattr(tf.keras.losses, loss)
    elif hasattr(tfa.losses, loss):
        loss_function = getattr(tfa.losses, loss)
    elif loss in ALLOWED_CUSTOM_LOSSES:
        # Get custom loss function.
        loss_function = getattr(losses, loss)
        if loss in NAN_VALUE_LOSSES:
            loss_arguments["nan_value"] = nan_value
    else:
        raise ValueError(f"Loss function {loss} is not valid.")
    if loss not in ALLOWED_CUSTOM_LOSSES and not isinstance(loss_function, type):
        raise ValueError("For keras or tensorflow losses, loss should be a class")
    try:
        return loss_function(**loss_arguments)
    except TypeError as e:
        raise TypeError("Wrong arguments to loss function.") from e


def load_existing_model_from_file(
    model_uri, loss="nan_mean_squared_error_loss", loss_arguments=None
):
    loss_arguments = loss_arguments or {}
    obj = tio.get(model_uri)
    fid = BufferedReader(obj._raw_stream)
    read_in_memory = fid.read()
    bio = BytesIO(read_in_memory)
    f = h5py.File(bio, "r")
    model_uri = f
    loss_function = load_loss_function(loss, loss_arguments)
    return tf.keras.models.load_model(
        model_uri,
        custom_objects={"loss": loss_function},
    )


def load_keras_model(
    model_config_uri, compile_args, loss_arguments=None, use_existing_model=False
):
    loss_name = compile_args.pop("loss", None)
    loss_arguments = loss_arguments or {}

    if use_existing_model:
        path_model = os.path.join(os.path.dirname(model_config_uri), "model.h5")
        model = load_existing_model_from_file(
            path_model, loss=loss_name, loss_arguments=loss_arguments
        )
    else:
        model = load_model(model_config_uri)
        loss_function = load_loss_function(loss_name, loss_arguments)
        model.compile(loss=loss_function, **compile_args)
    return model


class SaveModel(tf.keras.callbacks.Callback):
    """
    Custom Callback function to save and upload to remote storage models on epoch end.

    Parameters
    ----------
        passed_epochs : int
            Number of epochs already trained on the model.
        path : string
            Path to local or remote storage model folder.
    """

    def __init__(self, passed_epochs, path):
        self.passed_epochs = passed_epochs
        self.path = path
        super().__init__()

    def on_epoch_end(self, epoch, logs=None):
        epoch_number = epoch + self.passed_epochs + 1
        uri = os.path.join(self.path, f"model_epoch_{epoch_number}.hdf5")

        tio.save_model(uri, self.model)


class LogProgress(tf.keras.callbacks.Callback):
    """
    Custom Callback function to log training progress.
    """

    def __init__(self, name: str, uri: str):
        super().__init__()
        self.slack = SlackClient()
        self.model_name = name
        self.model_uri = uri

    def _log_status(self, state, logs=None, epoch=None):
        extra = logs or {}
        if epoch is not None:
            extra["current_epoch"] = epoch + 1
            extra["all_epochs"] = self.params["epochs"]
        self.slack.log_keras_progress(state, extra, self.model_name, self.model_uri)
        logger.info(state, **extra)

    def on_epoch_begin(self, epoch, logs=None):
        self._log_status("Epoch begin", logs, epoch)

    def on_epoch_end(self, epoch, logs=None):
        self._log_status("Epoch end", logs, epoch)

    def on_train_end(self, logs=None):
        self._log_status("Training end", logs)

    def on_test_end(self, logs=None):
        self._log_status("Evaluation end", logs)


@log_function
def train_model_function(
    catalog_uri,
    model_config_uri,
    model_compile_arguments_uri,
    model_fit_arguments_uri,
    generator_arguments_uri,
    model_name=None,
):
    """
    From a catalog and the configurations files build a model and train on the
    given data. Save the model.

    Parameters
    ----------
        catalog_uri : pystac catalog
            Catalog with the information where to download data.
        model_config_uri : path to json file
            File of dictionary containing the model configuration.
        model_compile_arguments_uri : path to json file
            File of dictionary containing the compilation arguments.
        model_fit_arguments_uri : path to json file
            File of dictionary containing the fit arguments.
        generator_arguments_uri : path to json file
            File of dictionary containing the generator configuration.
        model_name: optional string to identify the model in logs
    Returns
    -------
        model : tensorflow trained model
            Model trained with catalog data.
    """
    gen_args = tio.load_dictionary(generator_arguments_uri)
    GeneratorArgumentsValidator(**gen_args)
    compile_args = tio.load_dictionary(model_compile_arguments_uri)
    fit_args = tio.load_dictionary(model_fit_arguments_uri)
    path_model = os.path.join(os.path.dirname(model_config_uri), "model.h5")
    loss_arguments = compile_args.pop("loss_args", {})
    train_with_array = gen_args.pop("train_with_array", None)
    if gen_args.get("download_data"):
        tmpdir = tempfile.TemporaryDirectory()
        gen_args["download_dir"] = tmpdir.name

    use_existing_model = compile_args.pop("use_existing_model", False)
    if use_existing_model:
        last_training_epochs = len(
            tio.list_files(os.path.dirname(model_config_uri), suffix=".hdf5")
        )
    else:
        last_training_epochs = 0

    loss_arguments["nan_value"] = gen_args.get(
        "nan_value", gen_args.get("y_nan_value", None)
    )
    model = load_keras_model(
        model_config_uri, compile_args, loss_arguments, use_existing_model
    )
    gen_args["dtype"] = model.input.dtype.name
    eval_split = gen_args.pop("eval_split", 0)
    if "training_percentage" not in gen_args:
        gen_args["training_percentage"] = gen_args["split"]
    # Load the class weights from the Y catalog if requested. Class weights can
    # be passed as a dictionary with the class weights. In this case these
    # will be passed on and not altered. If the class weights key is present,
    # the class weights will be extracted from the Y catalog.
    if "class_weight" in fit_args and fit_args["class_weight"]:
        if isinstance(fit_args["class_weight"], dict):
            class_weight = fit_args["class_weight"]
        else:
            # Open x catalog.
            x_catalog = tio.load_dictionary(catalog_uri)
            # Get origin files zip link from dictionary.
            origin_files = [
                dat for dat in x_catalog["links"] if dat["rel"] == "origin_files"
            ][0]["href"]
            # Construct y catalog uri.
            y_catalog_uri = os.path.join(
                os.path.dirname(origin_files), "stac", "catalog.json"
            )
            # Open y catalog.
            y_catalog = tio.load_dictionary(str(y_catalog_uri))
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
    # Instantiate generator.
    catalog_path = os.path.join(os.path.dirname(catalog_uri), "catalogs_dict.json")
    gen_args["path_collection_catalog"] = catalog_path
    gen_args["usage_type"] = generator.GENERATOR_MODE_TRAINING
    dtgen = generator.DataGenerator(**gen_args)
    if dtgen.one_hot:
        fit_args.pop("class_weight")

    # Instantiate keras callbacks
    save_model = SaveModel(
        passed_epochs=last_training_epochs,
        path=os.path.dirname(model_config_uri),
    )
    log_progress = LogProgress(name=model_name, uri=model_uri(model_config_uri))

    if train_with_array:
        # Stack all items into one array.
        X = []
        Y = []
        samples_weights = []
        pixel_counter = 0
        for element in dtgen:
            X.append(element[0])
            Y.append(element[1])
            if gen_args.get("class_weights") and dtgen.one_hot:
                samples_weights.append(element[2])
            pixel_counter += element[1].shape[0]
            if pixel_counter > TRAIN_WITH_ARRAY_LIMIT:
                logger.warning(
                    "Training array limit reached, stopping collecting pixels. "
                    f"{pixel_counter} > {TRAIN_WITH_ARRAY_LIMIT}"
                )
                break
        X = np.vstack(X)
        Y = np.vstack(Y)
        if gen_args.get("class_weights") and dtgen.one_hot:
            samples_weights = np.hstack(samples_weights)
            fit_args["sample_weight"] = samples_weights
        # Fit model with data arrays.
        history = model.fit(
            X,
            Y,
            **fit_args,
            callbacks=[save_model, log_progress],
            verbose=0,
        )
    else:
        # Fit model with generator directly.
        history = model.fit(
            dtgen,
            **fit_args,
            callbacks=[save_model, log_progress],
            verbose=0,
        )
    # Write history.
    path_ep_md = os.path.dirname(tio.local_or_temp(model_config_uri))
    if not os.path.exists(path_ep_md):
        os.makedirs(path_ep_md)
    with open(os.path.join(path_ep_md, "history_stats.json"), "w") as f:
        # Get history data.
        hist_data = history.history
        # Write data.
        json.dump(hist_data, f, cls=NumpyArrayEncoder)

    tio.save_model(path_model, model)

    # Send history graph to slack
    graph_path = os.path.join(path_ep_md, "history_graph.png")
    plot_history(history.history, graph_path, model_name)
    SlackClient().send_history_graph(graph_path)

    # Evaluate model on test set.
    gen_args["usage_type"] = generator.GENERATOR_MODE_EVALUATION
    gen_args.pop("class_weights")
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
    results = model.evaluate(
        dpredgen,
        callbacks=[log_progress],
        verbose=0,
    )
    # Export evaluation statistics to json file.
    with open(os.path.join(path_ep_md, "evaluation_stats.json"), "w") as f:
        json.dump(results, f, cls=NumpyArrayEncoder)
    if tio.is_remote(model_config_uri):
        tio.upload(path_ep_md, suffix=".png", delete_original=False)
        tio.upload(path_ep_md, suffix="_stats.json")
    if gen_args.get("download_data"):
        tmpdir.cleanup()
    return model


@log_function
def predict_function_batch(
    model_uri,
    collection_uri,
    generator_config_uri,
    items_per_job,
):
    """
    From a trained model and the configurations files build the predictions on
    the given data. Save the predictions and pystac items representing them.

    Parameters
    ----------
        model_uri : keras model h5
            Trained model.
        generator_config_uri : path to json file
            File of dictionary containing the generator configuration.
        collection_uri : str, path
            Collection with the information from the input data.
        items_per_job : int
            Number of items per jobs.
    """
    gen_args = tio.load_dictionary(generator_config_uri)
    compile_args = tio.load_dictionary(
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

    # Instantiate generator, forcing generator to prediction mode.
    gen_args["batch_number"] = 1
    gen_args["usage_type"] = generator.GENERATOR_MODE_PREDICTION
    gen_args["dtype"] = model.input.dtype.name
    gen_args["x_nan_value"] = None

    # Extract generator arguments that are only for prediction and are not
    # passed to generator. These arguments need to be handled differently in a
    # future implementation. They are not really generator arguments but are
    # passed to this section through the generator arguments dictionary.
    jumping_ratio = gen_args.pop("jumping_ratio", 1)
    jump_pad = gen_args.pop("jump_pad", 0)
    extract_probabilities = gen_args.pop("extract_probabilities", False)
    rescale_probabilities = gen_args.pop("rescale_probabilities", False)
    clip_range = gen_args.pop("clip_range", False)

    catalog_path = os.path.join(os.path.dirname(collection_uri), "catalogs_dict.json")
    gen_args["path_collection_catalog"] = catalog_path
    dtgen = generator.DataGenerator(**gen_args)
    # Get parent folder for prediction.
    predict_path = os.path.dirname(generator_config_uri)
    # Get jobs array.
    array_index = int(os.getenv("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    item_list_max = (array_index + 1) * int(items_per_job)
    if item_list_max > len(dtgen):
        item_list_max = len(dtgen)
    item_list_min = array_index * int(items_per_job)
    item_range = range(item_list_min, item_list_max)
    logger.info(f"Predicting generator range from {item_list_min} to {item_list_max}.")
    model_upsampling = 1
    if dtgen.mode in MODE_PREDICTION_PER_IMAGE:
        # Index img number based on mode.
        if dtgen.mode in generator.GENERATOR_3D_MODES:
            width_index = 3
            height_index = 2
        else:
            width_index = 2
            height_index = 1
        model_upsampling = int(
            model.output_shape[1]
            / (model.input_shape[height_index] - (dtgen.padding * 2))
        )
        if model_upsampling == 0:
            model_upsampling = 1
    upsampling = int(dtgen.upsampling * model_upsampling)
    # Predict the index range for this batch job.
    for item in item_range:
        # Get metadata from index, and create paths.
        meta = dtgen.get_meta(item)
        if dtgen.mode in generator.GENERATOR_Y_IMAGE_MODES:
            # If the generator output is bigger than model shape, do a jumping window.
            if dtgen.mode in generator.GENERATOR_RESNET_MODES:
                big_square_width = dtgen.width
                big_square_height = dtgen.height
            else:
                big_square_width = dtgen.expected_x_shape[width_index]
                big_square_height = dtgen.expected_x_shape[height_index]

            big_square_width_result = (big_square_width * model_upsampling) - (
                dtgen.padding * 2
            )
            big_square_height_result = (big_square_height * model_upsampling) - (
                dtgen.padding * 2
            )
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
                # Instantiate empty result matrix.
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
                                j = big_square_height - (height - dtgen.padding)
                            if big_square_width - i < width:
                                res = data[:, :, j : j + height, -width:, :]
                                i = big_square_height - (width - dtgen.padding)
                            if (
                                big_square_height - j < height
                                and big_square_width - i < width
                            ):
                                res = data[:, :, -height:, -width:, :]
                                j = big_square_height - (height - dtgen.padding)
                                i = big_square_height - (width - dtgen.padding)
                        # If 2D mode break additional dimension.
                        if dtgen.mode == generator.GENERATOR_2D_MODEL:
                            res = res[:, 0]
                        pred = model.predict(res)
                        # Merge all predictions
                        jump_pad_j_i = jump_pad
                        jump_pad_j_f = jump_pad
                        jump_pad_i_i = jump_pad
                        jump_pad_i_f = jump_pad
                        if i == 0:
                            jump_pad_i_i = 0
                        if big_square_width - i <= jump_width:
                            jump_pad_i_f = 0
                        if big_square_width - i <= width:
                            jump_pad_i_f = 0
                            jump_pad_i_i = 0
                        if j == 0:
                            jump_pad_j_i = 0
                        if big_square_height - j <= jump_height:
                            jump_pad_j_f = 0
                        if big_square_height - j <= height:
                            jump_pad_j_f = 0
                            jump_pad_j_i = 0
                        # Get only the array without the padding.
                        pred = pred[
                            :,
                            jump_pad_j_i : pred.shape[1] - jump_pad_j_f,
                            jump_pad_i_i : pred.shape[2] - jump_pad_i_f,
                            :,
                        ]
                        # Make the iterators for the prediction big window.
                        j_pred = j * model_upsampling
                        i_pred = i * model_upsampling
                        jumping_height_pred = jumping_height * model_upsampling
                        # Get the image from the main prediction.
                        aux_pred = prediction[
                            :,
                            j_pred
                            + jump_pad_j_i : j_pred
                            + jumping_height_pred
                            - jump_pad_j_f,
                            i_pred
                            + jump_pad_i_i : i_pred
                            + jumping_height_pred
                            - jump_pad_i_f,
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
                            j_pred
                            + jump_pad_j_i : j_pred
                            + jumping_height_pred
                            - jump_pad_j_f,
                            i_pred
                            + jump_pad_i_i : i_pred
                            + jumping_height_pred
                            - jump_pad_i_f,
                            :,
                        ]
                        pred_sum = np.ones(pred.shape)
                        # Summed the new pixel with the old.
                        summed_pred = np.nansum([pred, aux_pred], axis=0)
                        prediction[
                            :,
                            j_pred
                            + jump_pad_j_i : j_pred
                            + jumping_height_pred
                            - jump_pad_j_f,
                            i_pred
                            + jump_pad_i_i : i_pred
                            + jumping_height_pred
                            - jump_pad_i_f,
                        ] = summed_pred
                        # Summed section of iteration on each pixel.
                        summed_iteration = np.sum([aux_sum, pred_sum], axis=0)
                        pred_num_it[
                            :,
                            j_pred
                            + jump_pad_j_i : j_pred
                            + jumping_height_pred
                            - jump_pad_j_f,
                            i_pred
                            + jump_pad_i_i : i_pred
                            + jumping_height_pred
                            - jump_pad_i_f,
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
        if dtgen.mode in MODE_PREDICTION_PER_PIXEL:
            image_shape = (meta["height"], meta["width"], dtgen.num_classes)
            prediction = np.array(prediction.reshape(image_shape))

        # Set the Y nodata value (defaults to none).
        meta["nodata"] = dtgen.y_nan_value

        # Limit the number of bands to be writen in the image file to 1.
        meta["count"] = 1

        # Ensure the class axis is the first one.
        if dtgen.mode in MODE_PREDICTION_PER_PIXEL:
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
            axis = 0 if dtgen.mode in MODE_PREDICTION_PER_PIXEL else 1
            prediction = np.argmax(prediction, axis=axis)
            # Ensure the maximum number of classes is not surpassed.
            if np.max(prediction) > 255:
                raise ValueError(
                    f"Model can not have more than 255 classes. Found {np.max(prediction)}."
                )
            # Rasterio expects shape to have the band number first. So expand
            # prediction shape from (height, width) to (1, height, width).
            if dtgen.mode in MODE_PREDICTION_PER_PIXEL:
                prediction = prediction.reshape(*(1, *prediction.shape))
            # Ensure prediction has a writable type. For now, we assume there
            # will not be more than 255 classes and use unit8. The default
            # argmax type is Int64 which is not a valid format for gdal.
            prediction = prediction.astype("uint8")
            meta["dtype"] = "uint8"

        # If requested, rescale the probabilities to integers from 0 to 255.
        # This keeps a reasonable precision and reduces the data size
        # substantially.
        if rescale_probabilities and (dtgen.num_classes == 1 or extract_probabilities):
            prediction = np.rint(prediction * 255).astype("uint8")
            # Override the nodata value and the datatype.
            meta["nodata"] = None
            meta["dtype"] = "uint8"

        # Conditions to be met when the probabilities are to be extracted.
        if extract_probabilities:
            # When probabilities are to be extracted the number of bands is the number of classes.
            meta["count"] = dtgen.num_classes
            if dtgen.mode in MODE_PREDICTION_PER_PIXEL:
                prediction = prediction.reshape(*(1, *prediction.shape))

        # Clip between the given range and rescale it to uint8.
        if clip_range:
            prediction = np.clip(prediction, clip_range[0], clip_range[1])
            prediction = (prediction - clip_range[0]) * (255 / clip_range[1])
            meta["dtype"] = "uint8"
            prediction = prediction.astype("uint8")
            meta["nodata"] = None

        # Compute target resolution using upscale factor.
        meta["transform"] = Affine(
            meta["transform"][0] / upsampling,
            meta["transform"][1],
            meta["transform"][2],
            meta["transform"][3],
            meta["transform"][4] / upsampling,
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
