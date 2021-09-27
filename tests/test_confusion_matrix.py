import unittest

import tensorflow as tf

from pixels.generator.multilabel_confusion_matrix import MultiLabelConfusionMatrix


class ConfusionMatrixTest(unittest.TestCase):
    def test_confusion_matrix(self):
        mlcm = MultiLabelConfusionMatrix(4)
        mlcm.update_state(
            tf.one_hot([0, 1, 2, 3, 0, 0, 1, 1], 4),
            tf.one_hot([0, 2, 1, 3, 0, 1, 0, 0], 4),
        )
        result = mlcm.result().numpy().tolist()
        expected = [
            [2, 1, 0, 0],
            [2, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
        ]
        self.assertEqual(result, expected)

    def test_confusion_matrix_reset_state(self):
        mlcm = MultiLabelConfusionMatrix(4)
        mlcm.update_state(
            tf.one_hot([0, 1, 2, 3, 0, 0, 1, 1], 4),
            tf.one_hot([0, 2, 1, 3, 0, 1, 0, 0], 4),
        )
        mlcm.reset_state()
        result = mlcm.result().numpy().tolist()
        expected = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        self.assertEqual(result, expected)

    def test_confusion_matrix_get_config(self):
        mlcm = MultiLabelConfusionMatrix(
            4, dtype="uint8", name="Speedy Gonzalez Matrix"
        )
        self.assertEqual(
            {"name": "Speedy Gonzalez Matrix", "dtype": "uint8", "num_classes": 4},
            mlcm.get_config(),
        )
