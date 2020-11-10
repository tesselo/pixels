from sqlalchemy import create_engine
import sqlalchemy as db
import psycopg2
import json, datetime

# Engine configuration -> Database URL
# dialect+driver://username:password@host:port/database
db_url = 'postgresql://postgres:postgres@localhost:5432/pixels'

# Connecting
engine = db.create_engine(db_url)
connection = engine.connect()
# metadata = db.MetaData()
# eo_index = db.Table('eo_index', metadata, autoload=True, autoload_with=engine)

# Function to search in API
def search_data(table, xmin, xmax, ymin, ymax, platform=None, start=None, end=None, maxcloud=None, limit=10):
    """ Query data from the eo_catalog DB """

    # SQL query template
    query = "SELECT base_url, product_id, sensing_time, mgrs_tile FROM {table} WHERE ST_Intersects(ST_MakeEnvelope({xmin}, {ymin},{xmax},{ymax},4326),geom)"

    # Check inputs
    if start is not None:
        query += ' AND sensing_time >= timestamp \'{}\' '.format(start)
    if end is not None:
        query += ' AND sensing_time <= timestamp \'{}\' '.format(end)
    if platform is not None:
        query += ' AND spacecraft_id = \'{}\' '.format(platform)
    if maxcloud is not None:
        query += ' AND cloud_cover <= {} '.format(maxcloud)
    if limit is not None:
        query += ' LIMIT {}'.format(limit)

    # Execute and format querry
    formatted_query = query.format(table=table,xmin=xmin, xmax=xmax,ymin=ymin, ymax=ymax)
    result = engine.execute(formatted_query)
    # print(' * ',formatted_query, ' * ')

    #Transform ResultProxy into json
    return [dict(row) for row in result]

#Templates
GOOGLE_URL = 'https://storage.cloud.google.com'
AWS_URL = ' https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs'

BASE_SENTINEL = 'gs://gcp-public-data-sentinel-2/tiles'
BASE_LANDSAT = 'gs:/'

S2_BANDS = [
    'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07',
    'B08', 'B8A', 'B10', 'B11', 'B12']

LS_BANDS = [ 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7',
    'B8', 'B9', 'B10', 'B11', 'BQA']


def get_bands(response):
    result = []
    for value in response:
        if 'sentinel-2' in value["base_url"]:
            value['bands'] =  format_sentinel_band(value)
        else:
            value['bands'] = format_ls_band(value)
        
        result.append(value)

    return result

def format_sentinel_band(value):
    # band_template_url = "{base_url}/{product_id}/{year}/{month}/{product_id}_{mgrstile}_{sensingtime}_0_L2A/{s2_band}"
    mgr = value["mgrs_tile"]
    utm_zone = mgr[:2]
    latitude_code = mgr[2:3]
    square_grid = mgr[3:5]
    base_url = AWS_URL
    date = datetime.datetime.strptime(str(value["sensing_time"]), '%Y-%m-%d %H:%M:%S.%f')
    product_id = value["product_id"]
    sensing_time = str(date.date()).replace('-', '')
    sequence = 0
    level = 'L2A'
    data ={}
    
    for band in S2_BANDS:
        band_template_url = "{base_url}/{utm}/{latitude}/{square_grid}/{year}/{month}/{product_id}_{mgr}_{sensing_time}_{sequence}_{level}/{band}.tif"
        data[band] = band_template_url.format(
            base_url=base_url,
            utm=utm_zone,
            latitude=latitude_code,
            square_grid=square_grid,
            year=date.year,
            month=date.month,
            product_id=product_id[:3],
            mgr=mgr,
            sensing_time=sensing_time,
            sequence=sequence,
            level=level,
            band=band)

    return data

def format_ls_band(value):

    product_id = value["product_id"]
    data = {}
    for band in LS_BANDS:

        base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT,GOOGLE_URL)
        ls_band_template = "{base_url}/{product_id}_{band}.TIF"
        
        data[band] = ls_band_template.format(
            base_url=base_url,
            product_id=product_id,
            band=band)

    return data


#tests
#result = get_bands(search_data(table='imagery', xmin=-48.461552, xmax=-48.445244, ymin=-1.482603 , ymax=-1.469732, start = '2020-01-01', end = '2020-01-10', maxcloud = 90))
#print(result)

