import unittest

import mock_functions
from pixels import core, utils
from tests.configs import gen_config, gen_configs


@unittest.mock.patch('pixels.scihub.warp_from_s3', mock_functions.warp_from_s3)
@unittest.mock.patch('pixels.core.search.search', mock_functions.search)
class TestPixels(unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()
