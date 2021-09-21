import numpy as np
import tensorflow as tf
from tensorflow.keras import backend as K


def root_mean_squared_error(y_true, y_pred):
    return K.sqrt(K.mean(K.square(y_pred - y_true)))


def nan_mean_squared_error_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        # if y_true.shape != y_pred.shape:
        #    y_true = y_true[:, :1]
        indices = tf.where(tf.not_equal(y_true, nan_value))
        return tf.keras.losses.mean_squared_error(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


def nan_categorical_crossentropy_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        indices = tf.where(tf.not_equal(y_true, nan_value))
        return tf.keras.losses.categorical_crossentropy(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


def nan_categorical_crossentropy_loss_drop_classe(nan_value=np.nan, classe_to_ignore=0):
    # Create a loss function to ignore classes on one-hot scheme, can be inputed as a list or a int.
    def loss(y_true, y_pred):
        y_true = np.delete(y_true, classe_to_ignore, -1)
        y_pred = np.delete(y_pred, classe_to_ignore, -1)
        indices = tf.where(tf.not_equal(y_true, nan_value))
        return tf.keras.losses.categorical_crossentropy(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


def nan_root_mean_squared_error_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        indices = tf.where(tf.not_equal(y_true, nan_value))
        return root_mean_squared_error(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


def nan_root_mean_squared_error_loss_more_or_less(nan_value=np.nan, less=True):
    # Create a loss function that only sees <= or >= than nan_value.
    def loss(y_true, y_pred):
        if less:
            indices = tf.where(tf.less_equal(y_true, nan_value))
        else:
            indices = tf.where(tf.greater_equal(y_true, nan_value))
        return root_mean_squared_error(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


def stretching_error_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        indices = tf.where(tf.not_equal(y_true, nan_value))
        truth = tf.gather_nd(y_true, indices)
        predictions = tf.gather_nd(y_pred, indices)
        error = abs(predictions - truth)
        return error * (truth + 1)

    # Return a function
    return loss


def square_stretching_error_loss(nan_value=np.nan):
    # Create a loss function
    def loss(y_true, y_pred):
        indices = tf.where(tf.not_equal(y_true, nan_value))
        truth = tf.gather_nd(y_true, indices)
        predictions = tf.gather_nd(y_pred, indices)
        error = abs(predictions - truth)
        return error * (truth + 1) * (truth + 1)

    # Return a function
    return loss
