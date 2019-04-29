import requests

from pixels import const

data = {
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
    "start": "2019-03-28",
    "end": "2019-04-01",
    "platform": const.PLATFORM_SENTINEL_2,
    "product_type": const.PRODUCT_L2A,
    "max_cloud_cover_percentage": 60,
    "search_only": False,
    "composite": True,
    "latest_pixel": False,
    "color": True,
    "format": 'PNG',
    "delay": False,
    # "bands": ["B04", "B03", "B02", "B08", "B05"],
}


# host = 'http://127.0.0.1:5000/data?key=829c0f290b9f0f0d49fd2501e5792f8413305535'
# host = 'https://pixels.tesselo.com/data'
host = 'https://devpixels.tesselo.com/data?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55'

result = requests.post(host, json=data)

#
# data.update({
#     'composite': False,
#     'latest_pixel': True
# })
# results.append(requests.post(host, json=data))
