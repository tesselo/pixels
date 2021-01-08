NODATA_VALUE = 0
S2_MAX_LUMINOSITY = 10000

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

S2_BANDS_10 = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]


LS_PLATFORMS = ["LANDSAT_7", "LANDSAT_8"] 

LANDSAT_1_LAUNCH_DATE = "1972-07-23"

# Search templates
GOOGLE_URL = "https://gcp-public-data-landsat.commondatastorage.googleapis.com"
AWS_URL = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs"
BASE_SENTINEL = "gs://gcp-public-data-sentinel-2/tiles"
BASE_LANDSAT = "gs://gcp-public-data-landsat"

# Platform Dates [min,max]
L1_DATES = ['1972-07-23', '1978-01-07']
L2_DATES = ['1975-01-24', '1982-02-18']
L3_DATES = ['1978-03-07', '1983-03-31']
L4_DATES = ['1982-08-06', '1993-11-18']
L5_DATES = ['1984-03-04', '2013-01-07']

# Actives
S2_DATES = '2015-06-27'
L7_DATES = '1999-05-28'
L8_DATES = '2013-03-08'

# Scaling
#80m - L1, L2
# 30m - L3,L4, L5
#L8_

# Sentinel 2:

# The L1C product quantization value has been set to 10 000: a Digital Number of
# 10 000 corresponds to a reflectance of 1, while a Digital Number of 1 represents
# a minimal value of the reflectance (0.001). The Digital Number 0 is a fill value
# (No Data), used for L1C pixels outside of the instrument observation swath.


# Datatype
# Platform Dates [min,max]
L1_DATES = ''
L2_DATES = ''
L3_DATES = ''
L4_DATES = ''
L5_DATES = ''

# Actives
S2_DATES = ''
L7_DATES = ''
L8_DATES = ''