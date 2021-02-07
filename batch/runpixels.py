#!/usr/bin/env python3.7
"""
Execute a function from the pixels package from the commandline.
"""
import importlib
import logging
import sys

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
)
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)
logging.getLogger("fiona").setLevel(logging.ERROR)

ALLOWED_MODULES = ["pixels.stac"]
ALLOWED_FUNCTIONS = ["parse_training_data"]


def main():
    print(sys.argv)
    # Get input function name.
    funk_path = sys.argv[1]
    # Get module for function.
    module_name = ".".join(funk_path.split(".")[:-1])
    logger.debug("Module name {}.".format(module_name))
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
    logger.debug("Function name {}.".format(funk_name))
    if funk_name not in ALLOWED_FUNCTIONS:
        raise ValueError(
            'Invalid input function. "{}" should be one of {}.'.format(
                funk_name, ALLOWED_FUNCTIONS
            )
        )
    funk = getattr(module, funk_name)
    logger.debug("Function args {}.".format(sys.argv[2:]))
    # Run function with rest of arguments.
    funk(*sys.argv[2:])


if __name__ == "__main__":
    main()
