import unittest
from unittest import mock

import numpy
from rasterio import Affine
from rasterio.io import MemoryFile

import mock_functions
from pixels import algebra, core, utils
from tests.configs import gen_config, gen_configs


@mock.patch('pixels.scihub.warp_from_s3', mock_functions.warp_from_s3)
@mock.patch('pixels.core.search.search', mock_functions.search)
class TestPixels(unittest.TestCase):

    @unittest.skip('Not fixed')
    def test_memory(self):
        config = gen_config({'mode': 'latest_pixel'})
        config = utils.validate_configuration(config)
        for i in range(1000):
            if i % 50 == 0:
                print('here ---------- ', i)
            core.handler(config)

    def test_pixels(self):
        for config in gen_configs():
            config = utils.validate_configuration(config)
            core.handler(config)

    def test_timeseries(self):
        config = gen_config({'interval': 'weeks', 'interval_step': 1})
        config = utils.validate_configuration(config)
        for here_start, here_end in utils.timeseries_steps(config['start'], config['end'], config['interval'], config['interval_step']):
            # Update config with intermediate timestamps.
            config.update({
                'start': str(here_start.date()),
                'end': str(here_end.date()),
            })
            # Trigger async task.
            core.handler(config)

    def test_algebra(self):
        height = width = 512
        creation_args = {
            'driver': 'GTiff',
            'dtype': 'uint16',
            'nodata': 0,
            'count': 1,
            'crs': 'epsg:4326',
            'transform': Affine(1, 0, 0, 0, -1, 0),
            'width': width,
            'height': height,
        }
        # Open memory destination file.
        memfile_b8 = MemoryFile()
        fake_data_b8 = (numpy.random.random((1, height, width)) * 1e3).astype('uint16')
        with memfile_b8.open(**creation_args) as rst:
            rst.write(fake_data_b8)

        memfile_b4 = MemoryFile()
        fake_data_b4 = (numpy.random.random((1, height, width)) * 1e3).astype('uint16')
        with memfile_b4.open(**creation_args) as rst:
            rst.write(fake_data_b4)
        # Evaluate formula.
        parser = algebra.FormulaParser()
        data = {'B08': memfile_b8, 'B04': memfile_b4}
        result = parser.evaluate(data, '(B08 - B04) / (B08 + B04)').ravel()
        # Evaluate expected array.
        expected = ((fake_data_b8.astype('float64') - fake_data_b4.astype('float64')) / (fake_data_b8.astype('float64') + fake_data_b4.astype('float64'))).ravel()
        # Arrays are equal.
        numpy.testing.assert_array_equal(result, expected)
        # Results are within expected range.
        self.assertFalse(numpy.any(result > 1.0))
        self.assertFalse(numpy.any(result < -1.0))


if __name__ == '__main__':
    unittest.main()
