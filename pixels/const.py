NODATA_VALUE = 0
S2_MAX_LUMINOSITY = 10000

# Bands
S2_BANDS = [
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B10",
    "B09",
    "B11",
    "B12",
]
LS_BANDS = [
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B9",
    "B10",
    "B11",
    "BQA",
]

# Bands combination
S2_BANDS_10 = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
L1_L2_L3_RGB = ["B6", "B5", "B4"]
L4_L5_L7_RGB = ["B3", "B2", "B1"]
L8_RGB = ["B4", "B3", "B2"]

# Platforms
LS_PLATFORMS = ["LANDSAT_7", "LANDSAT_8"]

# Search templates
GOOGLE_URL = "https://gcp-public-data-landsat.commondatastorage.googleapis.com"
AWS_URL = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs"
BASE_SENTINEL = "gs://gcp-public-data-sentinel-2/tiles"
BASE_LANDSAT = "gs://gcp-public-data-landsat"
AWS_L1C = "s3://sentinel-s2-l1c"

# Platform Dates [min,max]
L1_DATES = ["1972-07-23", "1978-01-07"]
L2_DATES = ["1975-01-24", "1982-02-18"]
L3_DATES = ["1978-03-07", "1983-03-31"]
L4_DATES = ["1982-08-06", "1993-11-18"]
L5_DATES = ["1984-03-04", "2013-01-07"]
LANDSAT_1_LAUNCH_DATE = "1972-07-23"

# Actives
S2_DATES = "2015-06-27"
L7_DATES = "1999-05-28"
L8_DATES = "2013-03-08"

# Scaling
L1 = 150
L2 = 150
L3 = 800
L4 = 100
S2_SCALE = 3000

# Modes to call pixels.
PIXELS_S2_STACK_MODE = "s2_stack"
PIXELS_LATEST_PIXEL_MODE = "latest_pixel"
PIXELS_COMPOSITE_MODE = "composite"
PIXELS_MODES = (PIXELS_S2_STACK_MODE, PIXELS_LATEST_PIXEL_MODE, PIXELS_COMPOSITE_MODE)
