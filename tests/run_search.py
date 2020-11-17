import datetime
import json

import geojson
import geopandas as gpd
import psycopg2
import sqlalchemy as db
from rasterio.features import bounds
from sqlalchemy import create_engine

from pixels.search import get_bands, search_data
from pixels.utils import compute_wgs83_bbox

geojson = {
    "type": "FeatureCollection",
    "name": "belem",
    "crs": {"init": "EPSG:3857"},
    "features": [{
        "type": "Feature",
        "properties": {
            "id": 1
        },
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-5401422.027732782997191, -153715.220885783957783],
                        [-5388736.031396471895278, -153480.139550630614394],
                        [-5388610.094966925680637, -164713.669066172820749],
                        [-5401195.342159599997103, -164856.397019658790668],
                        [-5401422.027732782997191, -153715.220885783957783]
                    ]
                ]
            ]
        }
    }]
}

# geojson= {
#     "type": "FeatureCollection",
#     "name": "belem_4326",
#     "crs": {"init": "EPSG:4326" },
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
#                         [-48.521799634922168, -1.380713670633853],
#                         [-48.407839390890238, -1.378602511270616],
#                         [-48.406708084695346, -1.47948362466969],
#                         [-48.519763283771368, -1.48076534389633],
#                         [-48.521799634922168, -1.380713670633853]
#                     ]
#                 ]
#             ]
#         }
#     }]
# }

#geojson = gpd.read_file('/home/keren/Desktop/belem.geojson')
result = get_bands(search_data(geojson, start = '1990-01-01', end = '2020-01-16', maxcloud=100, limit=1))
print(result)

