
import json
import os
import logging

import boto3
import numpy
import rasterio
from PIL import Image

from pixels.mosaic import latest_pixel_s2_stack
from batch.pyramid.tile_range import tile_range

logger = logging.getLogger()
# logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

s3 = boto3.client('s3')

bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
project_id = os.environ.get('PROJECT_ID', 'test')

# config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
# config = json.loads(config['Body'].read())

from shapely import wkt
from supermercado.burntiles import burn
studyarea = {
    "type": "FeatureCollection",
    "name": "aoi_lx_3857",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [4221106.735919824, -1736265.598606449],
                    [4193357.887847751, -1872923.001226717],
                    [4193357.887847751, -1872923.001226717],
                    [4168839.871963011, -2000260.921782380],
                    [4059250.149940649, -2146427.525249328],
                    [3957791.871378712, -2192621.624387202],
                    [3908895.935608357, -2423814.498744275],
                    [3746235.752146748, -2382705.686221981],
                    [3736327.010446677, -2426564.146185098],
                    [3575745.634752777, -2380980.764413798],
                    [3645024.390525834, -2029048.342937532],
                    [3805756.588984016, -2064205.766222333],
                    [3849309.791841074, -1842019.460616930],
                    [4026940.635842372, -1881828.503819331],
                    [4071817.876159736, -1710962.181728938],
                    [4221106.735919824, -1736265.598606449],
                ]]
            }
        },
    ]
}
import pyproj
from shapely.geometry import shape, mapping
from shapely.ops import transform
import mercantile

src_crs = pyproj.CRS('EPSG:3857')
dst_crs = pyproj.CRS('EPSG:4326')

project = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True).transform
rep = transform(project, shape(studyarea['features'][0]['geometry']))
rep = mapping(rep)
rep = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": rep,
        },
    ]
}

for i, (z, x, y) in enumerate(burn(rep['features'], 10)):
    print(i, z, x, y)
    bounds = mercantile.xy_bounds(x, y, z)
    geojson = {
        "type": "FeatureCollection",
        "crs": {"init": "EPSG:3857"},
        "features": [mercantile.feature((x, y, z), projected='mercator')]
    }

    # geojson = {
    # "type": "FeatureCollection",
    # "name": "aoi_lx_3857",
    # "crs": {"init": "EPSG:3857"},
    # "features": [
    # { "type": "Feature", "properties": { }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 4024590.964196575805545, -2097728.223975584376603 ], [ 4024489.84839366748929, -2106181.505098720081151 ], [ 4036118.165728124789894, -2106585.968310353346169 ], [ 4036037.27308579813689, -2097829.339778492692858 ], [ 4024590.964196575805545, -2097728.223975584376603 ] ] ] } }
    # # { "type": "Feature", "properties": { }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 3756530.622764486819506, -2185138.240627675782889 ], [ 3762642.811034350655973, -2185205.938915475271642 ], [ 3762652.482218321878463, -2189732.05301404511556 ], [ 3756530.622764486819506, -2189751.395381988026202 ], [ 3756530.622764486819506, -2185138.240627675782889 ] ] ] } }
    #
    # ]
    # }
    #
    result = latest_pixel_s2_stack(
        geojson,
        config['min_date'],
        config['max_date'],
        # config['scale'],
        1000,
        config['interval'],
        config['bands'],
        config['limit'],
        config['clip'],
        pool=False,
    )
# numpy.savez_compressed('/home/tam/Desktop/pixels_test/for_prediction2.npz', result=result)
# result = numpy.load('/home/tam/Desktop/pixels_test/for_prediction.npz', allow_pickle=True)['result']

X = numpy.array([dat[2] for dat in result])

# Print images.
# for i in range(25):
#     scene = X[i]
#     cloud_mask = cloud_or_snow(X[i, 8, :, :] / 1e4, X[i, 7, :, :] / 1e4, X[i, 6, :, :] / 1e4, X[i, 2, :, :] / 1e4, X[i, 1, :, :] / 1e4, X[i, 0, :, :] / 1e4, X[i, 9, :, :] / 1e4, False)
#     img = Image.fromarray(cloud_mask.astype('uint8') * 200)
#     img.save('/home/tam/Desktop/pixels_test/images/geom_2_scene_{}_clouds.png'.format(i))
#     rgb = [X[i][6], X[i][7], X[i][8]]
#     img = numpy.dstack([255 * (numpy.clip(dat, 0, 4000) / 4000) for dat in rgb]).astype('uint8')
#     img = Image.fromarray(img)
#     img.save('/home/tam/Desktop/pixels_test/images/geom_2_scene_{}_rgb.png'.format(i))

X = X.swapaxes(0, 2).swapaxes(1, 3)
X = X.reshape(X.shape[0] * X.shape[1], X.shape[2], X.shape[3])

cloud_mask = cloud_or_snow(X[:, :, 8], X[:, :, 7], X[:, :, 6], X[:, :, 2], X[:, :, 1], X[:, :, 0], X[:, :, 9])
X[cloud_mask] = 0

Y_predicted = model.predict(X)
Y_predicted = numpy.argmax(Y_predicted, axis=1) + 1

creation_args = result[0][0]
Y_predicted = Y_predicted.reshape(1, creation_args['height'], creation_args['width']).astype('uint16')

with rasterio.open('/home/tam/Desktop/pixels_test/prediction_geom_1_8_non_sequential_with_cloud_mask.tif', 'w', **creation_args) as dst:
    dst.write(Y_predicted)
