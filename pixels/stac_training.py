import json

import pixels.stac as stc
import pixels.stac_generator.generator_class as stcgen
import tensorflow as tf


def load_model_from_file(model_configuration_file):
    # Open config file and load as dict.
    if model_configuration_file.startswith("s3"):
        my_str = stc.open_file_from_s3(model_configuration_file)["Body"].read()
        new_str = my_str.decode("utf-8")
        input_config = json.loads(new_str)
    else:
        f = open(model_configuration_file)
        input_config = json.load(f)
    model_j = tf.keras.models.model_from_json(input_config)
    return model_j


def compile_model_from_file(model, model_compile_arguments):
    # Open config file and load as dict.
    if model_compile_arguments.startswith("s3"):
        my_str = stc.open_file_from_s3(model_compile_arguments)["Body"].read()
        new_str = my_str.decode("utf-8")
        input_config = json.loads(new_str)
    else:
        f = open(model_compile_arguments)
        input_config = json.load(f)
    model.compile(**input_config)
    return model


def get_fit_args(model_fit_arguments_uri):
    # Open config file and load as dict.
    if model_fit_arguments_uri.startswith("s3"):
        my_str = stc.open_file_from_s3(model_fit_arguments_uri)["Body"].read()
        new_str = my_str.decode("utf-8")
        input_config = json.loads(new_str)
    else:
        f = open(model_fit_arguments_uri)
        input_config = json.load(f)
    return input_config


def train_model_function(
    catalog_uri, model_config_uri, model_compile_arguments_uri, model_fit_arguments_uri
):
    dtgen = stcgen.DataGenerator_stac(catalog_uri, upsampling=10, timesteps=8)
    model = load_model_from_file(model_config_uri)
    model = compile_model_from_file(model, model_compile_arguments_uri)
    fit_args = get_fit_args(model_fit_arguments_uri)
    model.train(dtgen, **fit_args)
    model.save(model_config_uri.replace(".txt, .model"))
    return
