NODATA_VALUE = 0

S2_BANDS = [
    'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07',
    'B08', 'B8A', 'B10', 'B11', 'B12',
]
LS_BANDS = [
    'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7',
    'B8', 'B9', 'B10', 'B11', 'BQA',
]

S2_BANDS_10 = ['B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12']


LS_PLATFORMS=['LANDSAT_7', 'LANDSAT_8']

# Search templates
GOOGLE_URL = 'https://gcp-public-data-landsat.commondatastorage.googleapis.com'
AWS_URL = 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs'
BASE_SENTINEL = 'gs://gcp-public-data-sentinel-2/tiles'
BASE_LANDSAT = 'gs://gcp-public-data-landsat'
