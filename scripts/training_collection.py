import pprint

import requests

burned_pt_north = {
    "type": "Feature",
    "properties": {},
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-7.917194, 41.852365],
                [-7.917194, 41.857032],
                [-7.907152, 41.857032],
                [-7.907152, 41.852365],
                [-7.917194, 41.852365],
            ]
        ],
    },
    "crs": "EPSG:4326",
}
config = {
    "geom": burned_pt_north,
    "start": "2016-04-01",
    "end": "2019-04-01",
    "platform": "Sentinel-2",
    "product_type": "S2MSI1C",
    "max_cloud_cover_percentage": 100,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": False,
    "format": "NPZ",
    "delay": True,
    "scale": 20,
    "bands": ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
    # 'bands': ['B07'],
    "clip_to_geom": False,
    "interval": "weeks",
    "interval_step": 1,
}

# endpoint = 'https://pixels.tesselo.com/data?key=4bd45b2e090149dd5dfa7cdb10f48aa683354542'
endpoint = (
    "https://pixels.tesselo.com/timeseries?key=ac66322315e8b98cc7af954383ae6f01424a2fcb"
)
# endpoint = 'http://127.0.0.1:5000/timeseries?key=829c0f290b9f0f0d49fd2501e5792f8413305535'
# endpoint = 'https://devpixels.tesselo.com/timeseries?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55'

result = requests.post(endpoint, json=config)

print(result.status_code)
pprint.pprint(result.json())

# import glob
# import numpy
# for path in glob.glob('/home/tam/Desktop/bla/*.npz'):
#     print(path)
#     with open(path, 'rb') as fl:
#         try:
#             data = numpy.load(fl)
#             print(data['B02'])
#         except:
#             print('Failed')
#             raise


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
