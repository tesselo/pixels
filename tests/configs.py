import copy

BASE_CONFIG = {
    'geom': {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        -7.917194,
                        41.852365
                    ],
                    [
                        -7.917194,
                        41.857032
                    ],
                    [
                        -7.907152,
                        41.857032
                    ],
                    [
                        -7.907152,
                        41.852365
                    ],
                    [
                        -7.917194,
                        41.852365
                    ]
                ]
            ]
        },
        "crs": "EPSG:4326"
    },
    'start': '2019-03-01',
    'end': '2019-04-01',
    'platform': 'Sentinel-2',
    'product_type': 'S2MSI1C',
    'max_cloud_cover_percentage': 50,
    'search_only': False,
    'composite': False,
    'latest_pixel': True,
    'color': False,
    'format': 'NPZ',
    'delay': False,
    'scale': 10,
    'bands': ['B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12'],
    'clip_to_geom': True,
}


def gen_config(version):
    config = copy.deepcopy(BASE_CONFIG)
    config.update(version)
    return config


def gen_configs():
    versions = [
        {'format': 'PNG'},
        {'format': 'ZIP'},
        {'format': 'CSV'},
        {'composite': True, 'latest_pixel': False},
        {'bands': None},
        {'product_type': 'S2MSI2A'},
    ]

    return [gen_config(version) for version in versions]
