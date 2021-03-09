from pixels.search import search_data

geojson = {
    "type": "FeatureCollection",
    "name": "m_grande",
    "crs": {"init": "EPSG:3857"},
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-1006608.126849290914834, 4823706.554369583725929],
                        [-1006608.126849290914834, 4855094.944302001968026],
                        [-985360.601356576895341, 4855094.944302001968026],
                        [-985360.601356576895341, 4823706.554369583725929],
                        [-1006608.126849290914834, 4823706.554369583725929],
                    ]
                ],
            },
        },
    ],
}

result = search_data(
    geojson,
    start="2020-12-01",
    end="2021-01-01",
    maxcloud=50,
    limit=1,
    platforms="LANDSAT_1",
)


# import requests

# url = "http://127.0.0.1:5000/search"
# url = "https://pixels.tesselo.com/search?key=1c969a457a1e9936834e6db011375e2d00a5dca2"
# response = requests.post(
#     url,
#     json={
#         "geojson": geojson,
#         "start": "2020-01-01",
#         "end": "2020-10-16",
#         "maxcloud": 100,
#         # 'platforms': ['SENTINEL_2'],
#         "limit": 100,
#     },
# )
# print(len(response.json()))
