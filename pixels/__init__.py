import logging
import os

from kw.structlog_config import configure_stdlib_logging, configure_structlog
from pystac import STAC_IO

from pixels.stac.utils import read_method, write_method

STAC_IO.read_text_method = read_method
STAC_IO.write_text_method = write_method

__version__ = "0.1"

DEBUG = os.environ.get("DEBUG", False)
configure_structlog(debug=DEBUG, timestamp_format="iso")
configure_stdlib_logging(debug=DEBUG, timestamp_format="iso", level=logging.INFO)

# Stop the SPAM from botocore and rasterio
logging.getLogger("botocore.credentials").setLevel(logging.ERROR)
logging.getLogger("rasterio._filepath").setLevel(logging.CRITICAL + 1)
