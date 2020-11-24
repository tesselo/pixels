from pixels.const import LS_BANDS, LS_PLATFORMS
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
    start="2012-01-01",
    end="2020-01-16",
    maxcloud=100,
    platform=LS_PLATFORMS,
    limit=10,
)
print(result)
print(len(result))
# se retornar landsat 7 e 8 dar preferencia a 8!


# platform = 'SENTINEL_2'
# query += ' AND spacecraft_id IN {}'.format(str(tuple(platform)))
# result = spacecraft_id IN ('S', 'E', 'N', 'T', 'I', 'N', 'E', 'L', '_', '2') wrong

# platform = 'SENTINEL_2'
# query += ' AND spacecraft_id IN {}'.format(tuple(platform))
# result = spacecraft_id IN ('S', 'E', 'N', 'T', 'I', 'N', 'E', 'L', '_', '2') wrong

# platform = 'SENTINEL_2'
#  query += ' AND spacecraft_id IN {}'.format(platform)
#  = spacecraft_id IN SENTINEL_2  wrong


# platform = 'SENTINEL_2', 'LANDSAT_7'
#  query += ' AND spacecraft_id IN {}'.format(platform)
#  = spacecraft_id IN ('SENTINEL_2', 'LANDSAT_7') ok


# platform= "('LANDSAT_7')"
# query += ' AND spacecraft_id IN {}'.format(platform)
# spacecraft_id IN ('LANDSAT_7') ok

#  query += ' AND spacecraft_id IN {}'.format(tuple([platform])
# spacecraft_id IN ('LANDSAT_7',) wrong
