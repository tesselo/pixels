import tempfile
import unittest
from unittest import mock

import numpy
import rasterio
from rasterio import RasterioIOError

from pixels.retrieve import retrieve


def rasterio_open_mock(*args, **kwargs):
    if args[0].startswith("https"):
        raise RasterioIOError()
    else:
        raise ValueError(args[0])


class TestRetrieve(unittest.TestCase):
    def setUp(self):
        # Create temp raster.
        self.raster = tempfile.NamedTemporaryFile(suffix=".tif")
        scale = 10
        origin_x = -1028560.0
        origin_y = 4689560.0
        skew = 0
        size = 100
        self.creation_args = {
            "width": size,
            "height": size,
            "driver": "GTiff",
            "count": 1,
            "dtype": "uint16",
            "crs": "EPSG:3857",
            "nodata": 0,
            "transform": rasterio.Affine(scale, skew, origin_x, skew, -scale, origin_y),
        }
        with rasterio.open(self.raster.name, "w", **self.creation_args) as dst:
            dst.write(numpy.arange(size**2, dtype="uint16").reshape((1, size, size)))

        self.geojson = {
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

    def test_retrieve_values(self):
        # Should be same as original.
        self.geojson["features"][0]["geometry"]["coordinates"] = [
            [
                [-1028560.0, 4689560.0],
                [-1028560.0, 4688560.0],
                [-1027560.0, 4688560.0],
                [-1027560.0, 4689560.0],
                [-1028560.0, 4689560.0],
            ]
        ]
        result = retrieve(self.raster.name, self.geojson)
        size = 100
        numpy.testing.assert_array_equal(
            result[1],
            numpy.arange(size**2, dtype="uint16").reshape((size, size)),
        )

    def test_retrieve_creation_args(self):
        creation_args, data = retrieve(self.raster.name, self.geojson)
        self.creation_args["height"] = 56
        self.creation_args["width"] = 56
        self.creation_args["crs"] = rasterio.crs.CRS.from_epsg(3857)
        self.assertEqual(creation_args, self.creation_args)

    def test_retrieve_scale(self):
        # Default scale, retrieved from source raster.
        result = retrieve(self.raster.name, self.geojson)
        self.assertEqual(result[1].shape, (56, 56))
        # Custom scale.
        result = retrieve(self.raster.name, self.geojson, scale=5)
        self.assertEqual(result[1].shape, (112, 112))

    def test_retrieve_clip(self):
        # Clip default.
        result = retrieve(self.raster.name, self.geojson, clip=True, scale=250)
        expected = [
            [1453, 1475, 0],
            [3714, 0, 0],
            [0, 0, 0],
        ]
        numpy.testing.assert_array_equal(result[1], expected)
        # Clip with all touched.
        result = retrieve(
            self.raster.name, self.geojson, clip=True, all_touched=True, scale=250
        )
        expected = [
            [1453, 1475, 1500],
            [3714, 3737, 0],
            [6214, 0, 0],
        ]
        numpy.testing.assert_array_equal(result[1], expected)

    def test_retrieve_bands(self):
        # Add tow more bands.
        self.creation_args["count"] = 3
        size = 100
        with rasterio.open(self.raster.name, "w", **self.creation_args) as dst:
            dst.write(
                numpy.arange(3 * size**2, dtype="uint16").reshape((3, size, size))
            )
        # Default, gives all bands.
        result = retrieve(self.raster.name, self.geojson)
        self.assertEqual(result[1].shape, (3, 56, 56))
        # Test one band.
        result = retrieve(self.raster.name, self.geojson, bands=[1])
        self.assertEqual(result[1].shape, (56, 56))
        # Two bands.
        result = retrieve(self.raster.name, self.geojson, bands=[2, 3])
        self.assertEqual(result[1].shape, (2, 56, 56))
        # Three bands.
        result = retrieve(self.raster.name, self.geojson, bands=[1, 2, 3])
        self.assertEqual(result[1].shape, (3, 56, 56))

    def test_retrieve_discrete(self):
        result = retrieve(self.raster.name, self.geojson, discrete=True)
        self.assertEqual(result[1].shape, (56, 56))

    @mock.patch("pixels.retrieve.rasterio.open", rasterio_open_mock)
    def test_retrieve_cog_to_jp2(self):
        with self.assertRaisesRegex(ValueError, "s3://sentinel-s2-l2a"):
            retrieve(
                "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
                "sentinel-s2-l2a-cogs/29/S/ND/2021/12/S2B_29SND_20211215_0_L2A/B06.tif",
                self.geojson,
            )
