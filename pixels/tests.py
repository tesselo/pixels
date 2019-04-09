from pixels import const
from pixels.handler import handler
import requests

# target=/home/tam/Desktop/pixels
# sen2cor=/home/tam/Documents/repos/sen2cor
# pixels=/home/tam/Documents/repos/tesselo-scripts-collection/pixels
# export FLASK_ENV=development
# export FLASK_APP=pixels/app.py
# cp $pixels/*.py $target/pixels; cp $sen2cor/*.py $target/sen2cor; flask run
# cp $pixels/*.py $target/pixels; cp $sen2cor/*.py $target/sen2cor; ipython



event = {
  "geom": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [816091, 5946430],
            [816991, 5946430],
            [816991, 5945530],
            [816091, 5945530],
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
  "bands": const.SENTINEL_2_BANDS,
}
result = requests.post('http://127.0.0.1:5000/', json=event)

# result = handler(event, {})
#
# with open('/home/tam/Desktop/bands.zip', 'wb') as fl:
#     fl.write(result.getvalue())
