from pixels.const import LS_PLATFORMS
from pixels.search import search_data

# geojson = {
#     "type": "FeatureCollection",
#     "name": "belem",
#     "crs": {"init": "EPSG:3857"},
#     "features": [{
#         "type": "Feature",
#         "properties": {
#             "id": 1
#         },
#         "geometry": {
#             "type": "MultiPolygon",
#             "coordinates": [
#                 [
#                     [
#                         [-5401422.027732782997191, -153715.220885783957783],
#                         [-5388736.031396471895278, -153480.139550630614394],
#                         [-5388610.094966925680637, -164713.669066172820749],
#                         [-5401195.342159599997103, -164856.397019658790668],
#                         [-5401422.027732782997191, -153715.220885783957783]
#                     ]
#                 ]
#             ]
#         }
#     }]
# }

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

# geojson = gpd.read_file('/home/keren/Desktop/belem.geojson')
result = search_data(
    geojson,
    start='1972-07-23',
    end='1978-01-07',
    maxcloud=100,
    limit=10,
)
print(result)



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
