import numpy as np
import tensorflow as tf
from tensorflow.keras import backend as K
from tensorflow.keras.metrics import Metric
from tensorflow_addons.utils.types import AcceptableDTypes, FloatTensorLike
from typeguard import typechecked


class MultiLabelConfusionMatrix(Metric):
    """
    Computes Multi-label confusion matrix.
    Adapted from
    https://github.com/tensorflow/addons/blob/v0.14.0/tensorflow_addons/metrics/multilabel_confusion_matrix.py
    """

    @typechecked
    def __init__(
        self,
        num_classes: FloatTensorLike,
        name: str = "Multilabel_confusion_matrix",
        dtype: AcceptableDTypes = tf.dtypes.uint8,
        **kwargs,
    ):
        super().__init__(name=name, dtype=dtype)
        self.num_classes = num_classes
        self.confusion_matrix = self.add_weight(
            "confusion_matrix",
            shape=[self.num_classes, self.num_classes],
            initializer="zeros",
            dtype=self.dtype,
        )

    def update_state(self, y_true, y_pred, sample_weight=None):
        """
        Add counts to confusion matrix for this batch.
        """
        # Prepare emtpy confusion matrix.
        df_confusion = np.zeros((self.num_classes, self.num_classes))
        # Compute confusion for each class combination.
        for i in range(self.num_classes):
            for j in range(self.num_classes):
                # Compute match for the i and j classes.
                dat = tf.logical_and(
                    tf.cast(y_true[:, i], tf.dtypes.bool),
                    tf.cast(y_pred[:, j], tf.dtypes.bool),
                )
                # Sum the matches.
                df_confusion[i, j] = tf.reduce_sum(tf.cast(dat, tf.dtypes.uint8))
        # Add confusion to state.
        self.confusion_matrix.assign_add(
            tf.cast(tf.convert_to_tensor(df_confusion), self.dtype)
        )

    def result(self):
        return tf.convert_to_tensor(self.confusion_matrix)

    def get_config(self):
        """
        Returns the serializable config of the metric.
        """
        config = {
            "num_classes": self.num_classes,
        }
        base_config = super().get_config()
        return {**base_config, **config}

    def reset_state(self):
        reset_value = np.zeros((self.num_classes, self.num_classes), dtype=np.int32)
        K.batch_set_value([(v, reset_value) for v in self.variables])

    def reset_states(self):
        # Backwards compatibility alias of `reset_state`. New classes should
        # only implement `reset_state`.
        # Required in Tensorflow < 2.5.0
        return self.reset_state()
