import copy
import datetime
import io
import pprint

import fiona
import numpy
import pandas
import requests
from dateutil import parser
from shapely.geometry import shape

bands = ["B01"]

config = {
    "geom": {
        "type": "Feature",
        "crs": "EPSG:3857",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [916091, 5946430],  # Bern
                [915091, 5946430],
                [915091, 5945430],
                [916091, 5945430],
                [916091, 5946430],
            ]]
        },
    },
    'start': '2018-08-01',
    'end': '2018-08-18',
    'interval': 'weeks',
    "platform": 'Sentinel-2',
    "product_type": 'S2MSI1C',
    "s2_max_cloud_cover_percentage": 100,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": False,
    "format": 'ZIP',
    "delay": True,
    "scale": 20,
    "bands": [],
    "clip_to_geom": True,
    "interval": "weeks",
    "interval_step": 1,
}

shape_config = {
    'target_column': 'target',
    'feature_identifier_column': 'id',
}


# endpoint = 'https://pixels.tesselo.com/timeseries?key=b0ef31c1be11bede35c874ca6c5e5361e95598df'
endpoint = 'http://127.0.0.1:5000/timeseries?key=829c0f290b9f0f0d49fd2501e5792f8413305535'
# endpoint = 'https://devpixels.tesselo.com/data?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55'

result = requests.post(endpoint, json=config)

print(result.status_code)
pprint.pprint(result.json())

# 'http://127.0.0.1:5000/timeseries/be190e0e-eeb6-4677-b7bd-07ff974baeb2/data.zip?key=829c0f290b9f0f0d49fd2501e5792f8413305535'
# pprint.pprint(src[1])

#
# result = funk(config)
# result = results[0]
#
# result_npz = [numpy.load(io.BytesIO(requests.get(dat['url']).content)) for dat in result]
#
# result_np = [{band: dat[band].ravel() for band in (bands + ['config'])} for dat in result_npz]
#
# result_np = []
# for dat in result_npz:
#     tmp = {band: dat[band].ravel() for band in bands}
#     tmp['start'] = dat['config'].item()['start']
#     tmp['end'] = dat['config'].item()['end']
#     result_np.append(tmp)
#
# result_pd = [pandas.DataFrame(dat) for dat in result_np]
#
#
# print(result_pd)
