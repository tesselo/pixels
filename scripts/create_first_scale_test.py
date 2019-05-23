import json

with open('/home/tam/Desktop/celpa.geojson') as fl:
    data = json.loads(fl.read())
for dat in data['features']:
    dat['crs'] = 'EPSG:3857'

config = {
    "start": "2019-01-01",
    "end": "2019-05-10",
    "platform": "Sentinel-2",
    "product_type": "S2MSI1C",
    "max_cloud_cover_percentage": 100,
    "search_only": False,
    "composite": False,
    "latest_pixel": True,
    "color": False,
    "format": "NPZ",
    "delay": False,
    "scale": 10,
    "bands": ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
    "clip_to_geom": True,
    "interval": "weeks",
    "interval_step": 1,
    "train": data,
    "predict": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -8.943386,
                            38.511505
                        ],
                        [
                            -8.943386,
                            38.530173
                        ],
                        [
                            -8.880386,
                            38.530173
                        ],
                        [
                            -8.880386,
                            38.511505
                        ],
                        [
                            -8.943386,
                            38.511505
                        ]
                    ]
                ]
            },
            "crs": "EPSG:4326"
        }]
    }
}
with open('/home/tam/Desktop/config.json', 'w') as fl:
    fl.write(json.dumps(config))
