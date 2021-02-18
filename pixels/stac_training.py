import ast
import json
import os

import tensorflow as tf

import pixels.stac as stc
import pixels.stac_generator.generator_class as stcgen


def _load_dictionary(path_file):
    # Open config file and load as dict.
    if path_file.startswith("s3"):
        my_str = stc.open_file_from_s3(path_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        input_config = json.loads(new_str)
    else:
        with open(path_file, "r") as json_file:
            input_config = json_file.read()
        dict = ast.literal_eval(input_config)
    return dict


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
    path_model = os.path.join(os.path.dirname(catalog_uri), "model")
    model.save(path_model)
    if path_model.startswith("s3"):
        stc.upload_files_s3(path_model, file_type=".*")
    return model
