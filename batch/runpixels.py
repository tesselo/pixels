#!/usr/bin/env python
"""
Execute a function from the pixels package from the commandline.
"""
import os

import click
import sentry_sdk

from pixels.generator.prediction_utils import merge_prediction
from pixels.generator.stac import (
    build_catalog_from_items,
    collect_from_catalog_subsection,
    create_x_catalog,
    parse_training_data,
)
from pixels.generator.stac_training import predict_function_batch, train_model_function
from pixels.log import logger

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        # Sentry DSN is not a secret, but it should be added to a broader
        # configuration management policy and removed from here
        os.environ.get("SENTRY_DSN"),
        # Set traces_sample_rate to 0.1 to capture 10%
        traces_sample_rate=0.1,
    )


# List of modules and functions that can be specified in commandline input.
ALLOWED_MODULES = [
    "pixels.generator.stac",
    "pixels.generator.stac_training",
    "pixels.generator.prediction_utils",
]
ALLOWED_FUNCTIONS = {
    "parse_training_data": parse_training_data,
    "collect_from_catalog_subsection": collect_from_catalog_subsection,
    "create_x_catalog": create_x_catalog,
    "train_model_function": train_model_function,
    "predict_function_batch": predict_function_batch,
    "build_catalog_from_items": build_catalog_from_items,
    "merge_prediction": merge_prediction,
}


@click.command()
@click.argument("args", nargs=-1)
def main(args):
    """
    Import the requested function and run it with the provided input.
    """
    # print(args)
    # Get input function name.
    funk_path = args[0]
    # Get module for function.
    module_name = ".".join(funk_path.split(".")[:-1])
    logger.info(f"Module name {module_name}.")
    # Verify the requested module is in shortlist.
    if module_name not in ALLOWED_MODULES:
        raise ValueError(
            'Invalid input module. "{}" should be one of {}.'.format(
                module_name, ALLOWED_MODULES
            )
        )
    # Get function to execute.
    funk_name = funk_path.split(".")[-1]
    logger.info(f"Function name {funk_name}.")
    if funk_name not in ALLOWED_FUNCTIONS.keys():
        raise ValueError(
            f'Invalid input function. "{funk_name}" should be one of {ALLOWED_FUNCTIONS.keys()}.'
        )
    logger.info(f"Function args {args[1:]}.")
    # Run function with rest of arguments.
    ALLOWED_FUNCTIONS[funk_name](*args[1:])


if __name__ == "__main__":
    main()
