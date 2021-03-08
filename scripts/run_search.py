from pixels.search import search_data
from pixels.const import L1_DATES, L2_DATES, L3_DATES, L4_DATES, L5_DATES, L7_DATES, L8_DATES

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
# result = search_data(
#     geojson,
#     start="2020-12-01",
#     end="2021-01-01",
#     maxcloud=50,
#     limit=1,
#     platforms="LANDSAT_1",
# )

            
result = search_data(
            geojson,
            start=L8_DATES,
            end="2020-12-31",
            maxcloud=20,
            limit=1,
            platforms="LANDSAT_8") 
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
