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
        result = runner.invoke(
            main, ["pixels.generator.stac.not_valid_function", "arg1", "arg2"]
        )
        assert isinstance(result.exception, ValueError)
        assert result.exception.args[0].startswith("Invalid input function.")

    def test_train_model_function_correct_arguments_number(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "pixels.generator.stac_training.train_model_function",
                "s3://collection.json",
                "s3://model.json",
                "s3://compile_arguments.json",
                "s3://fit_arguments.json",
                "s3://generator_arguments.json",
            ],
        )
        # This test will exit in local will exit in a different point than in github
        # so we test that the exception is not the one that would result if the
        # number of arguments is wrong
        assert not isinstance(result.exception, TypeError)
        assert not result.exception.args[0].startswith("parse_data() missing")
