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
                [816091, 5946430],
                [817991, 5946430],
                [817991, 5935530],
                [816091, 5935530],
                [816091, 5946430],
            ]]
        },
    },
    "start": "2019-03-30",
    "end": "2019-04-01",
    "platform": const.PLATFORM_SENTINEL_2,
    "product_type": const.PRODUCT_L1C,
    "s2_max_cloud_cover_percentage": 100,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": True,
    "bands": ["B04", "B03", "B02"],
    # "bands": const.SENTINEL_2_BANDS,
}
result = requests.post('https://cu3qnyr749.execute-api.eu-central-1.amazonaws.com/dev/', json=event)
print(result)
with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
    fl.write(result.content)


event = {
    "geom": {
        "type": "Feature",
        "srs": "EPSG:3857",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [816091, 5946430],
                [826991, 5946430],
                [826991, 5935530],
                [816091, 5935530],
                [816091, 5946430],
            ]]
        },
    },
    "start": "2019-03-30",
    "end": "2019-04-01",
    "platform": const.PLATFORM_SENTINEL_2,
    "product_type": const.PRODUCT_L1C,
    "s2_max_cloud_cover_percentage": 100,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": True,
    "render": True,
    # "bands": ["B04", "B03", "B02"],
}

url = 'http://127.0.0.1:5000/?data={}'.format(urllib.quote(json.dumps(event)))
webbrowser.open(url, new=2)

event["start"] = "2019-01-01"
event["end"] = "2019-02-30"
event['platform'] = const.PLATFORM_SENTINEL_1
event['product_type'] = const.PRODUCT_GRD
event['s1_acquisition_mode'] = const.MODE_IW
url = 'http://127.0.0.1:5000/?data={}'.format(urllib.quote(json.dumps(event)))
webbrowser.open(url, new=2)

# print(url)
# result = requests.get(url)

result = requests.post('http://127.0.0.1:5000/', json=event)
print(result)

with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
    fl.write(result.content)
