import unittest

from click.testing import CliRunner

from batch.runpixels import main


class TestRetrieve(unittest.TestCase):
    def test_running_module_not_whitelisted(self):
        runner = CliRunner()
        result = runner.invoke(main, ["not.valid.module", "arg1", "arg2"])
        assert isinstance(result.exception, ValueError)
        assert result.exception.args[0].startswith("Invalid input module.")

    def test_running_function_not_whitelisted(self):
        runner = CliRunner()
        result = runner.invoke(main, ["pixels.stac.not_valid_function", "arg1", "arg2"])
        assert isinstance(result.exception, ValueError)
        assert result.exception.args[0].startswith("Invalid input function.")
