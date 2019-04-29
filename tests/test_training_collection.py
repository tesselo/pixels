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

from pixels import const

bands = ["B03"]

config = {
    "geom": {
        "type": "Feature",
        "crs": "EPSG:3857",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                # [916091, 5946430],  # Bern
                # [914091, 5946430],
                # [914091, 5944430],
                # [916091, 5944430],
                # [916091, 5946430],
                [-8685316, -161905],  # Puyo
                [-8680872, -161781],
                [-8680982, -166239],
                [-8685433, -166239],
                [-8685316, -161905],
            ]]
        },
    },
    'start': '2018-01-01',
    'end': '2019-03-31',
    # 'end': '2017-09-26',
    # 'start': '2017-08-30',
    'interval': 'weeks',
    "platform": 'Sentinel-2',
    "product_type": 'S2MSI1C',
    "max_cloud_cover_percentage": 100,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": True,
    "format": 'PNG',
    "delay": True,
    "scale": 10,
    # "bands": const.SENTINEL_2_BANDS,
    "clip_to_geom": False,
    "interval": "weeks",
    "interval_step": 1,
}

shape_config = {
    'target_column': 'target',
    'feature_identifier_column': 'id',
}


# endpoint = 'https://pixels.tesselo.com/timeseries?key=b0ef31c1be11bede35c874ca6c5e5361e95598df'
# endpoint = 'http://127.0.0.1:5000/timeseries?key=829c0f290b9f0f0d49fd2501e5792f8413305535'
endpoint = 'https://devpixels.tesselo.com/timeseries?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55'

result = requests.post(endpoint, json=config)

print(result.status_code)
pprint.pprint(result.json())

# import glob
# import numpy
# for path in glob.glob('/home/tam/Desktop/bla/*.npz'):
#     print(path)
#     with open(path) as fl:
#         data = numpy.load(fl)
#         print(data.keys())


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
