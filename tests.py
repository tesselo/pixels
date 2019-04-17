import json
import urllib
import webbrowser

import requests

from pixels import const

data = {
    "geom": {
        "type": "Feature",
        "srs": "EPSG:3857",
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
    "start": "2019-03-28",
    "end": "2019-04-01",
    "platform": const.PLATFORM_SENTINEL_2,
    "product_type": const.PRODUCT_L2A,
    "s2_max_cloud_cover_percentage": 60,
    "search_only": False,
    "composite": True,
    "latest_pixel": False,
    "color": True,
    "render": False,
    "delay": True,
    # "bands": ["B04", "B03", "B02", "B08", "B05"],
}


# host = 'http://127.0.0.1:5000'
host = 'https://pixels.tesselo.com'


results = []

# results.append(requests.post(host, json=data))

data.update({
    'composite': False,
    'latest_pixel': True
})
results.append(requests.post(host, json=data))

data.update({
    'render': True,
    'delay': False
})
url = '{}?data={}'.format(host, urllib.parse.quote(json.dumps(data)))
webbrowser.open(url)

# results.append(requests.post(host, json=data))
#
#
# data.update({
#     'color': False
# })
# results.append(requests.post(host, json=data))
#
# data.update({
#     'search_only': True,
#     'delay': False
# })
# results.append(requests.post(host, json=data))
#
# for res in results:
#     print(res.json())
