from pystac import STAC_IO

from pixels.stac.utils import read_method, write_method

STAC_IO.read_text_method = read_method
STAC_IO.write_text_method = write_method
