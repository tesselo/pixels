import json

import boto3
import rasterio
from rasterio.io import MemoryFile

from pixels import utils
from train.train import load_data

bucket='tesselo-pixels-results'
project_id='test'
data=load_data(bucket, project_id, 'result')
result = data['result']

# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

config['geom']=config['predict']['features'][0]
config = utils.validate_configuration(config)

transform, width, height, crs = utils.compute_transform(config['geom'], config['scale'])
creation_args = {
    'driver': 'GTiff',
    'crs': crs,
    'transform': transform,
    'width': width,
    'height': height,
    'nodata': 0,
    'dtype': 'uint8',
    'count': 1,
}
# with memfile.open(**creation_args) as rst:
with rasterio.open('/home/tam/Desktop/result.tif','w',**creation_args) as rst:
    rst.write(result.reshape(1, height, width).astype('uint8'))



# define GRU
model = Sequential()
model.add(BatchNormalization())
model.add(Bidirectional(GRU(250, dropout=0.3, recurrent_dropout=0.3)))
model.add(BatchNormalization())
model.to_json()
