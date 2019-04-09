from pixels import const
from pixels.handler import handler
import requests

event = {
  "geom": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [816091, 5946430],
            [818991, 5946430],
            [818991, 5925530],
            [816091, 5925530],
            [816091, 5946430]
        ]]
      },
      "srs": "EPSG:3857"
  },
  "start": "2019-03-30",
  "end": "2019-04-08",
  "platform": const.PLATFORM_SENTINEL_2,
  "product_type": const.PRODUCT_L1C,
  "s2_max_cloud_cover_percentage": 100,
  "search_only": False,
  "composite": True,
  "latest_pixel": False,
  "color": True,
  "bands": ["B02"]
  # "bands": const.SENTINEL_2_BANDS,
}
result = requests.post('https://cu3qnyr749.execute-api.eu-central-1.amazonaws.com/dev/', json=event); result

with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
    fl.write(result.content)

# result = requests.post('http://127.0.0.1:5000/', json=event); result

# with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
#     fl.write(result.getvalue())
