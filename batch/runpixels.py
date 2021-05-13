#!/usr/bin/env python3.7
"""
Execute a function from the pixels package from the commandline.
"""
import importlib
import logging.config
import sys

import sentry_sdk

sentry_sdk.init(
    # Sentry DSN is not a secret, but it should be added to a broader
    # configuration management policy and removed from here
    "https://3d69110c01aa41f48f28cf047bfcbc91@o640190.ingest.sentry.io/5760850",
    # Set traces_sample_rate to 1.0 to capture 100%
    traces_sample_rate=1.0,
)

# Logging configuration as dictionary.
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",  # Default is stderr
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["default"],
            "level": "ERROR",
            "propagate": False,
        },
        "pixels": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "runpixels": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}
# Set logging config.
logging.config.dictConfig(LOGGING_CONFIG)

# Get logger for the this module.
logger = logging.getLogger("runpixels")

# List of modules and functions that can be specified in commandline input.
ALLOWED_MODULES = ["pixels.stac", "pixels.stac_training"]
ALLOWED_FUNCTIONS = [
    "parse_training_data",
    "collect_from_catalog_subsection",
    "create_x_catalog",
    "train_model_function",
    "predict_function_batch",
    "build_catalog_from_items",
]


def main():
    """
    Import the requested function and run it with the provided input.
    """
    # Get input function name.
    funk_path = sys.argv[1]
    # Get module for function.
    module_name = ".".join(funk_path.split(".")[:-1])
    logger.info("Module name {}.".format(module_name))
    # Verify the requested module is in shortlist.
    if module_name not in ALLOWED_MODULES:
        raise ValueError(
            'Invalid input module. "{}" should be one of {}.'.format(
                module_name, ALLOWED_MODULES
            )
        )
    module = importlib.import_module(module_name)
    # Get function to execute.
    funk_name = funk_path.split(".")[-1]
    logger.info("Function name {}.".format(funk_name))
    if funk_name not in ALLOWED_FUNCTIONS:
        raise ValueError(
            'Invalid input function. "{}" should be one of {}.'.format(
                funk_name, ALLOWED_FUNCTIONS
            )
        )
    funk = getattr(module, funk_name)
    logger.info("Function args {}.".format(sys.argv[2:]))
    # Run function with rest of arguments.
    funk(*sys.argv[2:])


if __name__ == "__main__":
    main()
