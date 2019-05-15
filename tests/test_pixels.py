import unittest

import mock_functions
from pixels import core, utils
from tests.configs import gen_configs


@unittest.mock.patch('pixels.scihub.warp_from_s3', mock_functions.warp_from_s3)
@unittest.mock.patch('pixels.core.search.search', mock_functions.search)
class TestPixels(unittest.TestCase):

    def test_pixels(self):
        for config in gen_configs():
            config = utils.validate_configuration(config)
            core.handler(config)


if __name__ == '__main__':
    unittest.main()
