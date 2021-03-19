import numpy as np
import tensorflow as tf


def nan_mean_squared_error_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        if y_true.shape != y_pred.shape:
            y_true = y_true[:, :1]
        indices = tf.where(tf.not_equal(y_true, nan_value))
        return tf.keras.losses.mean_squared_error(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss
