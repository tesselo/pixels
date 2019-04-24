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

bands = ["B04", "B08"]

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
                # [-8685316, -161905],  # Puyo
                # [-8680872, -161781],
                # [-8680982, -166239],
                # [-8685433, -166239],
                # [-8685316, -161905],

            ]]
        },
    },
    'start': '2018-01-01',
    'end': '2018-01-16',
    'interval': 'weeks',
    "platform": 'Sentinel-2',
    "product_type": 'S2MSI1C',
    "s2_max_cloud_cover_percentage": 100,
    "search_only": True,
    "composite": False,
    "latest_pixel": True,
    "color": False,
    "format": 'NPZ',
    "delay": False,
    "bands": bands,
    "clip_to_geom": True,
}

def funk(config):
    start = parser.parse(config['start'])
    end = parser.parse(config['end'])
    print(start, end, start < end)

    assert start <= end

    delta = datetime.timedelta(**{config.pop('interval'): 1})
    here_start = start
    here_end = start + delta
    counter = 1
    results = []
    while here_end <= end:
        counter += 1
        here_end += delta
        here_start += delta
        print(here_start, here_end)
        config.update({
            'start': str(here_start.date()),
            'end': str(here_end.date()),
        })
        response = requests.post(endpoint, json=config)
        print(response.content)
        result = copy.deepcopy(config)
        result.update(response.json())
        results.append(result)

    return results
# endpoint = 'https://pixels.tesselo.com/data?key=b0ef31c1be11bede35c874ca6c5e5361e95598df'
# endpoint = 'http://127.0.0.1:5000/data?key=829c0f290b9f0f0d49fd2501e5792f8413305535'
endpoint = 'https://devpixels.tesselo.com/data?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55'

results = []
with fiona.open('/media/tam/rhino/work/projects/tesselo/projects/celpa/celpa_national/new_data/areas teste_28set2018.shp', 'r', encoding='latin-1') as src:
    for feat in src:
        config['geom'] = feat
        print(src.crs)
        config['geom']['crs'] = src.crs['init']
        results.append(funk(config))
        break

# pprint.pprint(src[1])

#
# result = funk(config)
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
