import json
import os
import tempfile
import unittest
import zipfile

import numpy
import pystac
import rasterio

from pixels.stac import parse_training_data


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
    data = numpy.arange(size ** 2, dtype="uint16").reshape((1, size, size))
    with rasterio.open(raster.name, "w", **creation_args) as dst:
        dst.update_tags(**tags)
        dst.write(data)
    return raster.name


class TestUtils(unittest.TestCase):
    def setUp(self, origin_x=-1028560.0, origin_y=4689560.0):
        # Create 3 temp raster.
        size = 256
        origin_x = -1028560.0
        origin_y = 4689560.0
        self.raster = []
        self.zip_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        raster = write_temp_raster()
        self.raster.append(raster)
        raster = write_temp_raster(origin_x=origin_x + size)
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
        href_1 = (
            "."
            + self.raster[0].replace(".tif", "")
            + self.raster[0].replace(".tif", "")
            + ".json"
        )
        href_2 = (
            "."
            + self.raster[1].replace(".tif", "")
            + self.raster[1].replace(".tif", "")
            + ".json"
        )
        href_3 = (
            "."
            + self.raster[2].replace(".tif", "")
            + self.raster[2].replace(".tif", "")
            + ".json"
        )

        self.catalog_example = {
            "id": self.zip_file.name.replace(
                os.path.dirname(self.zip_file.name), ""
            ).replace(".zip", ""),
            "stac_version": pystac.version.get_stac_version(),
            "description": "",
            "links": [
                {"rel": "root", "href": "./catalog.json", "type": "application/json"},
                {"rel": "item", "href": href_1, "type": "application/json"},
                {"rel": "item", "href": href_2, "type": "application/json"},
                {"rel": "item", "href": href_3, "type": "application/json"},
            ],
        }

    def test_parse_training_data(self):
        catalog = parse_training_data(self.zip_file.name, reference_date="2020-01-01")
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

        # Check content.
        with open(catalog.get_self_href(), "r") as myfile:
            data = myfile.read()
            # parse file
            obj = json.loads(data)

        self.assertEqual(obj, self.catalog_example)
