import unittest

from rasterio import path

from pixels.tio import open_zip


class TestZip(unittest.TestCase):
    def test_open_zip(self):
        zip_path = path.parse_path("file://tests/data/zip.zip!rick.jpg")
        opened = open_zip(zip_path)

        self.assertEqual(opened.filelist[0].filename, "rick.jpg")
