import json

import boto3

from pixels.mosaic import latest_pixel_s2_stack

config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())

geojson = {
    "type": "FeatureCollection",
    "name": "aoi_lx_3857",
    "crs": {"init": "EPSG:3857"},
    "features": [
        { "type": "Feature", "properties": { }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 4024590.964196575805545, -2097728.223975584376603 ], [ 4024489.84839366748929, -2106181.505098720081151 ], [ 4036118.165728124789894, -2106585.968310353346169 ], [ 4036037.27308579813689, -2097829.339778492692858 ], [ 4024590.964196575805545, -2097728.223975584376603 ] ] ] } }
    ]
}

result = latest_pixel_s2_stack(
    geojson,
    config['min_date'],
    config['max_date'],
    config['scale'],
    config['interval'],
    config['bands'],
    config['limit'],
    config['clip'],
    pool=False,
)
