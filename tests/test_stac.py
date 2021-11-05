import datetime
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy
import pystac
import rasterio

from pixels.generator.stac import (
    collect_from_catalog_subsection,
    create_x_catalog,
    parse_training_data,
)


def write_temp_raster(
    origin_x=-1028560.0, origin_y=4689560.0, scale=10, skew=0, size=256, tags={}
):
    # Create temp raster.
    raster = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    creation_args = {
        "width": size,
        "height": size,
        "driver": "GTiff",
        "count": 1,
        "dtype": "uint16",
        "crs": "EPSG:3857",
        "nodata": 0,
        "transform": rasterio.Affine(scale, skew, origin_x, skew, -scale, origin_y),
    }
    data = (
        numpy.array([0, 1, 2, 3] * int((size ** 2) / 4))
        .reshape((1, size, size))
        .astype("uint16")
    )
    with rasterio.open(raster.name, "w", **creation_args) as dst:
        dst.update_tags(**tags)
        dst.write(data)
    return raster.name


l8_return = MagicMock(
    return_value={
        "B1": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
        "B2": os.path.join(os.path.dirname(__file__), "data/B01.tif"),
    }
)

l8_data_mock = MagicMock(
    return_value=[
        {
            "product_id": "LC08_L1TP_205032_20201121_20201122_01_T1",
            "granule_id": None,
            "sensing_time": datetime.datetime(2020, 11, 21, 11, 20, 37, 137788),
            "mgrs_tile": None,
            "cloud_cover": Decimal("0.01"),
            "wrs_path": 85217265,
            "wrs_row": 85217265,
            "base_url": "gs://gcp-public-data-landsat/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_T1",
        },
        {
            "product_id": "LC08_L1TP_205032_20201121_20201122_01_T1",
            "granule_id": None,
            "sensing_time": datetime.datetime(2020, 11, 20, 11, 20, 37, 137788),
            "mgrs_tile": None,
            "cloud_cover": Decimal("0.01"),
            "wrs_path": 85217265,
            "wrs_row": 85217265,
            "base_url": "gs://gcp-public-data-landsat/LC08/01/205/032/LC08_L1TP_205032_20201121_20201122_01_T1",
        },
    ]
)


class TestUtils(unittest.TestCase):
    def setUp(self, origin_x=-1028560.0, origin_y=4689560.0):
        self.maxDiff = None
        # Create 3 temp raster.
        size = 256
        origin_x = -1028560.0
        origin_y = 4689560.0
        self.raster = []
        self.zip_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        raster = write_temp_raster(tags={"datetime": "2021-01-01"})
        self.raster.append(raster)
        raster = write_temp_raster(
            origin_x=origin_x + size, tags={"datetime": "2021-01-01"}
        )
        self.raster.append(raster)
        raster = write_temp_raster(
            origin_y=origin_y + size, tags={"datetime": "2021-01-01"}
        )
        self.raster.append(raster)

        # Zip them.
        with zipfile.ZipFile(self.zip_file.name, "w") as zipF:
            for file in self.raster:
                zipF.write(file, compress_type=zipfile.ZIP_DEFLATED)
        # Build example catalog based on temporary file names.
        id_name = "tmp"
        href_1 = (
            "./"
            + os.path.join(
                os.path.split(self.raster[0])[-1].replace(".tif", ""),
                os.path.split(self.raster[0])[-1].replace(".tif", ""),
            )
            + ".json"
        )
        href_2 = (
            "./"
            + os.path.join(
                os.path.split(self.raster[1])[-1].replace(".tif", ""),
                os.path.split(self.raster[1])[-1].replace(".tif", ""),
            )
            + ".json"
        )
        href_3 = (
            "./"
            + os.path.join(
                os.path.split(self.raster[2])[-1].replace(".tif", ""),
                os.path.split(self.raster[2])[-1].replace(".tif", ""),
            )
            + ".json"
        )

        self.catalog_example = {
            "id": id_name,
            "stac_version": pystac.version.get_stac_version(),
            "description": "",
            "class_weight": {"0": 0.25, "1": 0.25, "2": 0.25, "3": 0.25},
            "links": [
                {"rel": "root", "href": "./catalog.json", "type": "application/json"},
                {"rel": "item", "href": href_1, "type": "application/json"},
                {"rel": "item", "href": href_2, "type": "application/json"},
                {"rel": "item", "href": href_3, "type": "application/json"},
            ],
        }

        self.item_example = {
            "type": "Feature",
            "stac_version": "1.0.0-beta.2",
            "properties": {
                "driver": "GTiff",
                "dtype": "uint16",
                "nodata": 0.0,
                "width": 256,
                "height": 256,
                "count": 1,
                "crs": {"init": "epsg:3857"},
                "transform": [
                    10.0,
                    0.0,
                    -1028560.0,
                    0.0,
                    -10.0,
                    4689560.0,
                    0.0,
                    0.0,
                    1.0,
                ],
                "proj:epsg": 3857,
                "stac_extensions": ["projection"],
                "stats": {"0": 16384, "1": 16384, "2": 16384, "3": 16384},
                "datetime": "2021-01-01T00:00:00Z",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-1028560.0, 4687000.0],
                        [-1028560.0, 4689560.0],
                        [-1026000.0, 4689560.0],
                        [-1026000.0, 4687000.0],
                        [-1028560.0, 4687000.0],
                    ]
                ],
            },
            "links": [
                {"rel": "root", "href": "../catalog.json", "type": "application/json"},
                {
                    "rel": "parent",
                    "href": "../catalog.json",
                    "type": "application/json",
                },
            ],
            "bbox": [-1028560.0, 4687000.0, -1026000.0, 4689560.0],
        }

    def tearDown(self):
        """
        Remove some temp files.
        """
        if os.path.exists(self.zip_file.name):
            os.remove(self.zip_file.name)
        for path in self.raster:
            if os.path.exists(path):
                os.remove(path)

    def test_parse_training_data(self):
        catalog = parse_training_data(
            self.zip_file.name, True, reference_date="2020-01-01"
        )
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

        # Check content of catalog.
        with open(catalog.get_self_href(), "r") as myfile:
            data = myfile.read()
            obj = json.loads(data)
        self.assertEqual(obj, self.catalog_example)

        # Check content of first item.
        item = [item for item in catalog.get_all_items()][0]
        with open(item.get_self_href(), "r") as myfile:
            data = myfile.read()
            obj = json.loads(data)
        # Pop the varying parts that are due to the random paths and IDs.
        obj.pop("id")
        obj.pop("assets")
        self.assertEqual(obj, self.item_example)

    @patch("pixels.search.conn_pixels.execute", l8_data_mock)
    @patch("pixels.search.format_ls_c1_band", l8_return)
    def test_collect_from_catalog_subsection(self):
        catalog = parse_training_data(
            self.zip_file.name, True, reference_date="2020-01-01"
        )
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
        target = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile(suffix=".json", dir=target) as fl:
            config = {
                "bands": [
                    "B1",
                    "B2",
                ],
                "clip": False,
                "start": "2020-01-01",
                "end": "2020-02-01",
                "interval": "all",
                "maxcloud": 30,
                "pool_size": 1,
                "scale": 500,
                "platforms": "LANDSAT_8",
            }
            fl.write(bytes(json.dumps(config).encode("utf8")))
            fl.seek(0)
            nr_of_items = 3
            collect_from_catalog_subsection(
                catalog.get_self_href(), fl.name, nr_of_items
            )
            create_x_catalog(target, self.zip_file.name)
        # Open the collection.
        with open(os.path.join(target, "data/collection.json"), "r") as myfile:
            obj = json.loads(myfile.read())
        # Remove the links with varying temp paths.
        links = obj.pop("links")
        # The rest of the collection is as expected.
        expected = {
            "id": f"x_collection_{target.split('/')[-1]}",
            "stac_version": "1.0.0-beta.2",
            "description": "",
            "title": "",
            "extent": {
                "spatial": {"bbox": [[-1028560.0, 4686560.0, -1025304.0, 4689816.0]]},
                "temporal": {
                    "interval": [["2020-11-20T00:00:00Z", "2020-11-21T00:00:00Z"]]
                },
            },
            "license": "proprietary",
        }
        self.assertEqual(obj, expected)
        # A link to the zip training file is present.
        self.assertIn({"rel": "origin_files", "href": self.zip_file.name}, links)
        # Number of links is as expected.
        self.assertEqual(len(links), 12)
        # Cleanup.
        shutil.rmtree(target)
