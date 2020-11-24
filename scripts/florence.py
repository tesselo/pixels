# https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html
# https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip
import json
import os

import requests

path = "/home/tam/Documents/repos/pixels/scripts/florence.json"

florence = json.load(open(path))
# host = 'https://pixels.tesselo.com/data?key=92da6c69c6daff2d9bff9de87763f82e667fcc06'
host = "http://127.0.0.1:5000/data?key=829c0f290b9f0f0d49fd2501e5792f8413305535"

result = requests.post(host, json=florence)

print(result.content)
