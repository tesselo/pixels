import json
import urllib
import webbrowser

import requests

from pixels import const

event = {
    "geom": {
        "type": "Feature",
        "srs": "EPSG:3857",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [816091, 5946430],  # Bern
                [817191, 5946430],
                [817291, 5945430],
                [816091, 5945430],
                [816091, 5946430],

                # [-8685316, -161905],  # Puyo
                # [-8680872, -161781],
                # [-8680982, -166239],
                # [-8685433, -166239],
                # [-8685316, -161905],

            ]]
        },
    },
    "start": "2019-01-01",
    "end": "2019-04-10",
    "platform": const.PLATFORM_SENTINEL_2,
    "product_type": const.PRODUCT_L2A,
    "s2_max_cloud_cover_percentage": 50,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": True,
    "render": True,
    "delay": False,
    # "bands": ["B04", "B03", "B02"],
}


# host = 'https://cu3qnyr749.execute-api.eu-central-1.amazonaws.com/dev/'
host = 'http://127.0.0.1:5000/pixels'
url = '{}?data={}'.format(host, urllib.parse.quote(json.dumps(event)))
result = requests.get(url)
print(result.content)
# webbrowser.open(url, new=2)

# webbrowser.open('http://127.0.0.1:5000/13/4092/2723', new=2)
# # Sentinel-1
# event["start"] = "2019-01-01"
# event["end"] = "2019-02-30"
# event['platform'] = const.PLATFORM_SENTINEL_1
# event['product_type'] = const.PRODUCT_GRD
# event['s1_acquisition_mode'] = const.MODE_IW
#
# url = 'http://127.0.0.1:5000/?data={}'.format(urllib.parse.quote(json.dumps(event)))
# webbrowser.open(url, new=2)

# print(url)
# result = requests.get(url)

# result = requests.post('http://127.0.0.1:5000/', json=event)
# print(result)
#
# with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
#     fl.write(result.content)

# result = requests.post('https://cu3qnyr749.execute-api.eu-central-1.amazonaws.com/dev/', json=event)
# print(result)
# with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
#     fl.write(result.content)
