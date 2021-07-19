#!/usr/bin/env python3.7
"""
Execute a function from the pixels package from the commandline.
"""
import importlib
import logging
import os
import sys

import click
import sentry_sdk
import structlog

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        # Sentry DSN is not a secret, but it should be added to a broader
        # configuration management policy and removed from here
        os.environ.get("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        traces_sample_rate=1.0,
    )

# Set structlog logging config.
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Set standard logging config.
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

# Get logger for the this module.
logger = structlog.get_logger("runpixels")

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
    logger.info("Function args {}.".format(args[1:]))
    # Run function with rest of arguments.
    funk(*args[1:])


if __name__ == "__main__":
    main()
