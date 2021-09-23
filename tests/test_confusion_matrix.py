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
