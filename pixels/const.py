NODATA_VALUE = 0
S2_MAX_LUMINOSITY = 10000
INTEGER_NODATA_VALUE = 255
FLOAT_NODATA_VALUE = -9999

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

# Platforms
LS_PLATFORMS = ["LANDSAT_7", "LANDSAT_8"]

# Search templates
GOOGLE_URL = "https://gcp-public-data-landsat.commondatastorage.googleapis.com"
S2_L2A_URL = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs"
S2_L1C_URL = "s3://sentinel-s2-l1c"
LS_L2_URL = "s3://usgs-landsat/collection02/level-2/standard"
BASE_SENTINEL = "gs://gcp-public-data-sentinel-2/tiles"
BASE_LANDSAT = "gs://gcp-public-data-landsat"


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

# Cloud min value
L8_MIN_CLOUD_VALUE = 10000

# Platforms const
SENTINEL_2 = "SENTINEL_2"
LANDSAT_1 = "LANDSAT_1"
LANDSAT_2 = "LANDSAT_2"
LANDSAT_3 = "LANDSAT_3"
LANDSAT_4 = "LANDSAT_4"
LANDSAT_5 = "LANDSAT_5"
LANDSAT_7 = "LANDSAT_7"
LANDSAT_8 = "LANDSAT_8"

LANDSAT_SERIES = [
    LANDSAT_1,
    LANDSAT_2,
    LANDSAT_3,
    LANDSAT_4,
    LANDSAT_5,
    LANDSAT_7,
    LANDSAT_8,
]

# Const fort each band name
BAND_COASTAL = "coastal"
BAND_BLUE = "blue"
BAND_GREEN = "green"
BAND_RED = "red"
BAND_VRE1 = "vre1"
BAND_VRE2 = "vre2"
BAND_VRE3 = "vre3"
BAND_NIR1 = "nir1"
BAND_NIR2 = "nir2"
BAND_WV = "wv"
BAND_CIRRUS = "cirrus"
BAND_SWIR1 = "swir1"
BAND_SWIR2 = "swir2"
BAND_PAN = "pan"
BAND_THERMAL1 = "tirsi"
BAND_THERMAL2 = "tirsii"

# Create bands list for each platform
L4_5_SENSOR_ID = "TM"
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
    "B09",
    "B10",
    "B11",
    "B12",
]
# At L2A Band 10 does no longer exist, as it is only an atmosphere band. The SCL
# layer is a scene class layer produced by the Sen2Cor algorithm. It contains
# a simple cloud mask amongst other classes.
S2_BANDS_L2A = [
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B09",
    "B11",
    "B12",
    "SCL",
]

S2_BAND_RESOLUTIONS = {
    "B01": 60,
    "B02": 10,
    "B03": 10,
    "B04": 10,
    "B05": 20,
    "B06": 20,
    "B07": 20,
    "B08": 10,
    "B8A": 20,
    "B09": 60,
    "B10": 60,
    "B11": 20,
    "B12": 20,
    "SCL": 20,
}

L8_BANDS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
L7_BANDS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"]
L4_L5_BANDS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
L4_L5_BANDS_MSS = ["B1", "B2", "B3", "B4"]
L1_L2_L3_BANDS = ["B4", "B5", "B6", "B7"]
LS_COGS_BANDS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
DISCRETE_BANDS = ["SCL"]

# Bands for composite mode.
S2_BANDS_REQUIRED_FOR_COMPOSITES = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12"]

# Create const dict for band correspondence for each platform
BANDS_CORRESPONDENCE_S2 = {
    BAND_COASTAL: "B01",
    BAND_BLUE: "B02",
    BAND_GREEN: "B03",
    BAND_RED: "B04",
    BAND_VRE1: "B05",
    BAND_VRE2: "B06",
    BAND_VRE3: "B07",
    BAND_NIR1: "B08",
    BAND_NIR2: "B8A",
    BAND_WV: "B09",
    BAND_CIRRUS: "B10",
    BAND_SWIR1: "B11",
    BAND_SWIR2: "B12",
    BAND_PAN: None,
    BAND_THERMAL1: None,
    BAND_THERMAL2: None,
}


BANDS_CORRESPONDENCE_L8 = {
    BAND_COASTAL: "B1",
    BAND_BLUE: "B2",
    BAND_GREEN: "B3",
    BAND_RED: "B4",
    BAND_VRE1: None,
    BAND_VRE2: None,
    BAND_VRE3: None,
    BAND_NIR1: "B5",
    BAND_NIR2: None,
    BAND_WV: None,
    BAND_CIRRUS: "B9",
    BAND_SWIR1: "B6",
    BAND_SWIR2: "B7",
    BAND_PAN: "B8",
    BAND_THERMAL1: "B10",
    BAND_THERMAL2: "B11",
}

BANDS_CORRESPONDENCE_L7 = {
    BAND_COASTAL: None,
    BAND_BLUE: "B1",
    BAND_GREEN: "B2",
    BAND_RED: "B3",
    BAND_VRE1: None,
    BAND_VRE2: None,
    BAND_VRE3: None,
    BAND_NIR1: "B4",
    BAND_NIR2: None,
    BAND_WV: None,
    BAND_CIRRUS: None,
    BAND_SWIR1: "B5",
    BAND_SWIR2: "B7",
    BAND_PAN: "B8",
    BAND_THERMAL1: "B6",
    BAND_THERMAL2: "B6",
}

BANDS_CORRESPONDENCE_L4_L5 = {
    BAND_COASTAL: None,
    BAND_BLUE: "B1",
    BAND_GREEN: "B2",
    BAND_RED: "B3",
    BAND_VRE1: None,
    BAND_VRE2: None,
    BAND_VRE3: None,
    BAND_NIR1: "B4",
    BAND_NIR2: None,
    BAND_WV: None,
    BAND_CIRRUS: None,
    BAND_SWIR1: "B5",
    BAND_SWIR2: "B7",
    BAND_PAN: None,
    BAND_THERMAL1: "B6",
    BAND_THERMAL2: "B6",
}

BANDS_CORRESPONDENCE_L1_L2_L3 = {
    BAND_COASTAL: None,
    BAND_BLUE: None,
    BAND_GREEN: "B4",
    BAND_RED: "B5",
    BAND_VRE1: None,
    BAND_VRE2: None,
    BAND_VRE3: None,
    BAND_NIR1: "B6",
    BAND_NIR2: "B7",
    BAND_WV: None,
    BAND_CIRRUS: None,
    BAND_SWIR1: None,
    BAND_SWIR2: None,
    BAND_PAN: None,
    BAND_THERMAL1: None,
    BAND_THERMAL2: None,
}


# Create a dict with all bands correspondence according to platform
BANDS_CORRESPONDENCE_ALL = {
    SENTINEL_2: BANDS_CORRESPONDENCE_S2,
    LANDSAT_8: BANDS_CORRESPONDENCE_L8,
    LANDSAT_7: BANDS_CORRESPONDENCE_L7,
    LANDSAT_5: BANDS_CORRESPONDENCE_L4_L5,
    LANDSAT_4: BANDS_CORRESPONDENCE_L4_L5,
    LANDSAT_3: BANDS_CORRESPONDENCE_L1_L2_L3,
    LANDSAT_2: BANDS_CORRESPONDENCE_L1_L2_L3,
    LANDSAT_1: BANDS_CORRESPONDENCE_L1_L2_L3,
}

# Create formulas dict correspondence
FORMULAS = {
    "idx": [
        "infrared",
        "rgb",
        "swi",
        "agriculture",
        "geology",
        "bathymetric",
        "ndvi",
        "ndmi",
        "ndwi1",
        "ndwi2",
        "nhi",
        "savi",
        "gdvi",
        "evi",
        "nbr",
        "bai",
        "chlorogreen",
    ],
    "combination": [
        "nir1,red,green",
        "red,green,blue",
        "swir2,nir1,red",
        "swir1,nir1,blue",
        "swir2,swir1,blue",
        "red,green,coastal",
        "(nir1-red)/(nir1+red)",
        "(nir1-swir1)/(nir1+swir1)",
        "(green-swir1)/(green+swir1)",
        "(green-nir1)/(green+nir1)",
        "(swir1-green)/(swir1+green)",
        "(nir1-red)/(nir1+red+0.5)*(1.0+0.5)",
        "nir1-green",
        "2.5*(nir1-red)/(nir1+6*red-7.5*blue)+1",
        "(nir1-swir2)/(nir1+swir2)",
        "(blue-nir1)/(nir1+blue)",
        "nir1/(green+vre1)",
    ],
    "bands": [
        [BAND_NIR1, BAND_RED, BAND_GREEN],
        [BAND_RED, BAND_GREEN, BAND_BLUE],
        [BAND_SWIR1, BAND_NIR1, BAND_RED],
        [BAND_SWIR1, BAND_NIR1, BAND_BLUE],
        [BAND_SWIR2, BAND_SWIR1, BAND_BLUE],
        [BAND_RED, BAND_GREEN, BAND_COASTAL],
        [BAND_NIR1, BAND_RED],
        [BAND_NIR1, BAND_SWIR1],
        [BAND_GREEN, BAND_SWIR1],
        [BAND_GREEN, BAND_NIR1],
        [BAND_SWIR1, BAND_GREEN],
        [BAND_NIR1, BAND_RED],
        [BAND_NIR1, BAND_GREEN],
        [BAND_NIR1, BAND_RED, BAND_BLUE],
        [BAND_NIR1, BAND_SWIR2],
        [BAND_BLUE, BAND_NIR1],
        [BAND_NIR1, BAND_GREEN, BAND_VRE3],
    ],
}

# Landsat - Collection 2 - Level 2 COG items
L8_COG_ITEMS = {
    "SR_B1",
    "SR_B2",
    "SR_B3",
    "SR_B4",
    "SR_B5",
    "SR_B6",
    "SR_B7",
    "ST_QA",
    "ST_B10",
    "ST_DRAD",
    "ST_EMIS",
    "ST_EMSD",
    "ST_TRAD",
    "ST_URAD",
    "QA_PIXEL",
    "ST_ATRAN",
    "ST_CDIST",
    "QA_RADSAT",
    "SR_QA_AEROSOL",
}

L7_COG_ITEMS = {
    "SR_B1",
    "SR_B2",
    "SR_B3",
    "SR_B4",
    "SR_B5",
    "SR_B7",
    "ST_B6",
    "ST_QA",
    "ST_DRAD",
    "ST_EMIS",
    "ST_EMSD",
    "ST_TRAD",
    "ST_URAD",
    "QA_PIXEL",
    "ST_ATRAN",
    "ST_CDIST",
    "QA_RADSAT",
    "SR_ATMOS_OPACITY",
    "SR_CLOUD_QA",
}

L4_L5_COG_ITEMS = {
    "SR_B1",
    "SR_B2",
    "SR_B3",
    "SR_B4",
    "SR_B5",
    "SR_B7",
    "ST_B6",
    "QA_RADSAT",
    "QA_PIXEL",
    "ST_QA",
    "SR_ATMOS_OPACITY",
    "SR_CLOUD_QA",
    "ST_TRAD",
    "ST_URAD",
    "ST_DRAD",
    "ST_ATRAN",
    "ST_EMIS",
    "ST_EMSD",
    "ST_CDIST",
}

LS_BANDS_NAMES = [
    "red",
    "blue",
    "green",
    "nir08",
    "swir16",
    "swir22",
    "coastal",
    "qa_pixel",
    "qa_radsat",
]
LS_LOOKUP = {
    "red": "B4",
    "blue": "B2",
    "green": "B3",
    "nir08": "B5",
    "swir16": "B6",
    "swir22": "B7",
    "coastal": "B1",
    "qa_pixel": "QA_PIXEL",
    "qa_radsat": "QA_SAT",
}

WORKERS_LIMIT = 12
MAX_COMPOSITE_BAND_WORKERS = 10

SCENE_CLASS_RANK_FLAT = (
    8,  # NO_DATA
    7,  # SATURATED_OR_DEFECTIVE
    5,  # DARK_AREA_PIXELS
    5,  # CLOUD_SHADOWS
    1,  # VEGETATION
    2,  # NOT_VEGETATED
    3,  # WATER
    6,  # UNCLASSIFIED
    6,  # CLOUD_MEDIUM_PROBABILITY
    7,  # CLOUD_HIGH_PROBABILITY
    6,  # THIN_CIRRUS
    4,  # SNOW
)

# SCL classes.
# 0: NO_DATA
# 1: SATURATED_OR_DEFECTIVE
# 2: DARK_AREA_PIXELS
# 3: CLOUD_SHADOWS
# 4: VEGETATION
# 5: NOT_VEGETATED
# 6: WATER
# 7: UNCLASSIFIED
# 8: CLOUD_MEDIUM_PROBABILITY
# 9: CLOUD_HIGH_PROBABILITY
# 10: THIN_CIRRUS
# 11: SNOW
SCL_COMPOSITE_CLOUD_BANDS = [0, 1, 3, 7, 8, 9, 10]
