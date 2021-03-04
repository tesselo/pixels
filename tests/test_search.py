import unittest
from unittest import mock


from pixels.search import search_data


def mock_sqlalchemy():

    class MockSqlAlchemy():

        def create_engine(self, db_url, client_encoding="utf8"):

            class MockEngine():

                def connect(self, db_url, client_encoding="utf8"):
                    print('Faking connection.')
                    return 'Mocked engine'

                def execute(self, query):
                    print('Faking query.')
                    return [
                        {"result1": 1},
                        {"result2": 2},
                    ]
            return MockEngine()


def mock_create_engine(self, db_url, client_encoding="utf8"):

    class MockEngine():

        def connect(self, db_url, client_encoding="utf8"):
            print('Faking connection.')
            return 'Mocked engine'

        def execute(self, query):
            print('Faking query.')
            return [
                {"result1": 1},
                {"result2": 2},
            ]
    return MockEngine()


@mock.patch("pixels.search.create_engine", mock_create_engine)
class TestSearch(unittest.TestCase):

    def test_latest_pixel(self):
        geojson = {
            "type": "FeatureCollection",
            "crs": {"init": "EPSG:3857"},
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-1028560.0, 4689560.0],
                                [-1028560.0, 4689000.0],
                                [-1028000.0, 4689560.0],
                                [-1028560.0, 4689560.0],
                            ]
                        ],
                    },
                },
            ],
        }
        search_data(
            geojson,
            start=None,
            end=None,
            platforms=['Sentinel_2'],
            maxcloud=None,
            scene=None,
            level=None,
            limit=10,
            sort="sensing_time",
        )
