import numpy

# Base constants.
WGS84 = 'EPSG:4326'

QUERY_URL = 'https://scihub.copernicus.eu/dhus/search?q={search}&rows=100&start=0&format=json&sortedby=beginposition&order=desc'

QUERY_URL_MAX_LENGTH = 6000  # Total url max length on scihub is 8000.

BASE_SEARCH = '( footprint:"Intersects({geom})" ) AND ( beginPosition:[{start}T00:00:00.000Z TO {end}T23:59:59.999Z] AND endPosition:[{start}T00:00:00.000Z TO {end}T23:59:59.999Z] ) AND ( ( platformname:{platform} AND producttype:{product_type} AND {extra} ) )'

BUCKET = 'tesselo-pixels-results'

REQUEST_FORMAT_ZIP = 'ZIP'
REQUEST_FORMAT_PNG = 'PNG'
REQUEST_FORMAT_NPZ = 'NPZ'
REQUEST_FORMAT_CSV = 'CSV'

REQUEST_FORMATS = [REQUEST_FORMAT_ZIP, REQUEST_FORMAT_PNG, REQUEST_FORMAT_NPZ, REQUEST_FORMAT_CSV]

MAX_AREA = 100000 ** 2  # 100km by 100km

MAX_PIXEL_SIZE = 20000

TIMESERIES_WEEKLY = 'weeks'
TIMESERIES_MONTHLY = 'months'
TIMESERIES_INTERVALS = [TIMESERIES_MONTHLY, TIMESERIES_WEEKLY]

PIXELS_MIN_ZOOM = 12

# Modes.
MODE_SEARCH_ONLY = 'search_only'
MODE_LATEST_PIXEL = 'latest_pixel'
MODE_COMPOSITE = 'composite'
MODE_COMPOSITE_INCREMENTAL = 'composite_incremental'
MODE_COMPOSITE_NN = 'composite_nn'
MODE_COMPOSITE_INCREMENTAL_NN = 'composite_incremental_nn'


MODES = [MODE_SEARCH_ONLY, MODE_LATEST_PIXEL, MODE_COMPOSITE, MODE_COMPOSITE_INCREMENTAL, MODE_COMPOSITE_NN, MODE_COMPOSITE_INCREMENTAL_NN]

# ###################################################
# Sentinel-1
# ###################################################

SEARCH_SENTINEL_1 = 'sensoroperationalmode:{sensoroperationalmode}'

PLATFORM_SENTINEL_1 = 'Sentinel-1'

PRODUCT_GRD = 'GRD'
PRODUCT_SLC = 'SLC'
PRODUCT_OCN = 'OCN'

MODE_SM = 'SM'
MODE_IW = 'IW'
MODE_EW = 'EW'
MODE_WV = 'WV'

AWS_DATA_BUCKET_SENTINEL_1_L1C = 'sentinel-s1-l1c'

PREFIX_S1 = '{product_type}/{year}/{month}/{day}/{mode}/{polarisation}/{product_identifier}/'
# Example: 's3://sentinel-s1-l1c/GRD/2018/1/11/EW/DH/S1A_EW_GRDH_1SDH_20180111T110409_20180111T110513_020106_02247C_FBAB/ '
SENTINEL_1_BANDS_HH = ['HH']
SENTINEL_1_BANDS_VV = ['VV']
SENTINEL_1_BANDS_VV_VH = ['VV', 'VH']
SENTINEL_1_BANDS_HH_HV = ['HH', 'HV']

SENTINEL_1_POLARISATION_MODE = {
    'SH': SENTINEL_1_BANDS_HH,  # (single HH polarisation)
    'SV': SENTINEL_1_BANDS_VV,  # (single VV polarisation)
    'DH': SENTINEL_1_BANDS_HH_HV,  # (dual HH+HV polarisation)
    'DV': SENTINEL_1_BANDS_VV_VH,  # (dual VV+VH polarisation)
}

# ###################################################
# Sentinel-2
# ###################################################

SEARCH_SENTINEL_2 = 'cloudcoverpercentage:[0 TO {cloudcoverpercentage}]'

PLATFORM_SENTINEL_2 = 'Sentinel-2'

PRODUCT_L1C = 'S2MSI1C'
PRODUCT_L2A = 'S2MSI2A'

PROCESSING_LEVEL_S2_L1C = 'Level-1C'
PROCESSING_LEVEL_S2_L2A = 'Level-2A'

AWS_DATA_BUCKET_SENTINEL_2_L1C = 'sentinel-s2-l1c'
AWS_DATA_BUCKET_SENTINEL_2_L2A = 'sentinel-s2-l2a'

PREFIX_S2 = 'tiles/{utm}/{lz}/{grid}/{year}/{month}/{day}/'
# Example: 's3://sentinel-s2-l1c/tiles/29/S/NC/2016/3/21/'

SENTINEL_2_DTYPE = 'uint16'

SENTINEL_2_NODATA = 0

SENTINEL_2_BANDS = [
    'B01',
    'B02',
    'B03',
    'B04',
    'B05',
    'B06',
    'B07',
    'B08',
    'B8A',
    'B09',
    'B10',
    'B11',
    'B12',
]

SENTINEL_2_RGB_BANDS = ['B04', 'B03', 'B02']

SENTINEL_2_RGB_CLIPPER = 8e3

SENTINEL_2_RESOLUTION_LOOKUP = {
    'B01': '60',
    'B02': '10',
    'B03': '10',
    'B04': '10',
    'B05': '20',
    'B06': '20',
    'B07': '20',
    'B08': '10',
    'B8A': '20',
    'B09': '60',
    'B10': '60',
    'B11': '20',
    'B12': '20',
    'SCL': '20',
}

SCENE_CLASS_RANK_FLAT = (
    8,   # NO_DATA
    7,   # SATURATED_OR_DEFECTIVE
    5,   # DARK_AREA_PIXELS
    5,   # CLOUD_SHADOWS
    1,   # VEGETATION
    2,   # NOT_VEGETATED
    3,   # WATER
    5,   # UNCLASSIFIED
    6,   # CLOUD_MEDIUM_PROBABILITY
    7,   # CLOUD_HIGH_PROBABILITY
    6,   # THIN_CIRRUS
    4,   # SNOW
)

SCENE_CLASS_INCLUDE = (
    0,   # NO_DATA
    0,   # SATURATED_OR_DEFECTIVE
    1,   # DARK_AREA_PIXELS
    0,   # CLOUD_SHADOWS
    1,   # VEGETATION
    1,   # NOT_VEGETATED
    1,   # WATER
    1,   # UNCLASSIFIED
    0,   # CLOUD_MEDIUM_PROBABILITY
    0,   # CLOUD_HIGH_PROBABILITY
    0,   # THIN_CIRRUS
    1,   # SNOW
)

# Raster Algebra section
# Define all mappings between operators and string representations.
ALGEBRA_PIXEL_TYPE_GDAL = 7
ALGEBRA_PIXEL_TYPE_NUMPY = "Float64"

LPAR = "("
RPAR = ")"

NUMBER = r"[+-]?\d+(\.\d*)?([Ee][+-]?\d+)?"

VARIABLE_NAME_SEPARATOR = "_"
BAND_INDEX_SEPARATOR = ":"

# Keywords
EULER = "E"
PI = "PI"
TRUE = "TRUE"
FALSE = "FALSE"
NULL = "NULL"
INFINITE = "INF"

KEYWORD_MAP = {
    EULER: numpy.e,
    PI: numpy.pi,
    TRUE: True,
    FALSE: False,
    NULL: NULL,
    INFINITE: numpy.inf,
}

# Operator strings
ADD = "+"
SUBTRACT = "-"
MULTIPLY = "*"
DIVIDE = "/"
POWER = "^"
EQUAL = "=="
NOT_EQUAL = "!="
GREATER = ">"
GREATER_EQUAL = ">="
LESS = "<"
LESS_EQUAL = "<="
LOGICAL_OR = "|"
LOGICAL_AND = "&"
LOGICAL_NOT = "!"
FILL = "~"
UNARY_AND = "unary +"
UNARY_LESS = "unary -"
UNARY_NOT = "unary !"
UNARY_FILL = "unary ~"

# Operator groups
ADDOP = (ADD, SUBTRACT, )
POWOP = (POWER, )
UNOP = (ADD, SUBTRACT, LOGICAL_NOT, FILL)
# The order the operators in this group matters due to "<=" being caught by "<".
MULTOP = (
    MULTIPLY,
    DIVIDE,
    EQUAL,
    NOT_EQUAL,
    GREATER_EQUAL,
    LESS_EQUAL,
    GREATER,
    LESS,
    LOGICAL_AND,
    LOGICAL_OR
)

# Map operator symbols to arithmetic operations in numpy
OPERATOR_MAP = {
    ADD: numpy.add,
    SUBTRACT: numpy.subtract,
    MULTIPLY: numpy.multiply,
    DIVIDE: numpy.divide,
    POWER: numpy.power,
    EQUAL: numpy.equal,
    NOT_EQUAL: numpy.not_equal,
    GREATER: numpy.greater,
    GREATER_EQUAL: numpy.greater_equal,
    LESS: numpy.less,
    LESS_EQUAL: numpy.less_equal,
    LOGICAL_OR: numpy.logical_or,
    LOGICAL_AND: numpy.logical_and,
}

UNARY_OPERATOR_MAP = {
    UNARY_AND: numpy.array,
    UNARY_LESS: numpy.negative,
    UNARY_NOT: numpy.logical_not,
    UNARY_FILL: numpy.ma.filled,
}

UNARY_REPLACE_MAP = {
    ADD: UNARY_AND,
    SUBTRACT: UNARY_LESS,
    LOGICAL_NOT: UNARY_NOT,
    FILL: UNARY_FILL,
}

# Map function names to numpy functions
FUNCTION_MAP = {
    "sin": numpy.sin,
    "cos": numpy.cos,
    "tan": numpy.tan,
    "log": numpy.log,
    "exp": numpy.exp,
    "abs": numpy.abs,
    "int": numpy.int,
    "round": numpy.round,
    "sign": numpy.sign,
    "min": numpy.min,
    "max": numpy.max,
    "mean": numpy.mean,
    "median": numpy.median,
    "std": numpy.std,
    "sum": numpy.sum,
}
