#!/usr/bin/env python3.7
"""
Execute a function from the pixels package from the commandline.
"""
import importlib
import logging
import sys

logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)
logging.getLogger("fiona").setLevel(logging.ERROR)


def main():
    # Get input function name.
    funk_path = sys.argv[0]
    # Ensure input is from pixels.
    if not funk_path.split(".")[0] == "pixels":
        raise ValueError(
            "Expected pixels module, got {}".format(funk_path.split(".")[0])
        )
    # Get module for function.
    module_name = ".".join(funk_path.split(".")[:-1])
    logger.debug("Module name {}.".format(module_name))
    module = importlib.import_module(module_name)
    # Get function to execute.
    funk_name = ".".join(funk_path.split(".")[-1])
    logger.debug("Function name {}.".format(funk_name))
    funk = getattr(module, funk_name)
    logger.debug("Function args {}.".format(sys.argv[1:]))
    # Run function with rest of arguments.
    funk(*sys.argv[1:])


if __name__ == "__main__":
    main()
