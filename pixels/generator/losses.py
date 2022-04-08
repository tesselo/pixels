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


def nan_categorical_crossentropy_loss(nan_value=np.nan, class_with_nan=None):
    # Create a loss function
    def loss(y_true, y_pred):
        sparse = tf.math.argmax(y_true, axis=-1)
        indices = tf.where(tf.not_equal(sparse, class_with_nan))
        return tf.keras.losses.categorical_crossentropy(
            tf.gather_nd(y_true, indices), tf.gather_nd(y_pred, indices)
        )

    # Return a function
    return loss


def nan_categorical_crossentropy_loss_drop_classe(nan_value=np.nan, class_to_ignore=0):
    # Create a loss function to ignore classes on one-hot scheme, can be input as a list or an int.
    if isinstance(class_to_ignore, int):
        class_to_ignore = [class_to_ignore]

    def loss(y_true, y_pred):
        class_dimension = K.ndim(y_true) - 1
        mask_class = np.full(y_pred.shape[-1], True)
        mask_class[class_to_ignore] = False
        y_true = tf.boolean_mask(y_true, mask_class, axis=class_dimension)
        y_pred = tf.boolean_mask(y_pred, mask_class, axis=class_dimension)
        return tf.keras.losses.categorical_crossentropy(y_true, y_pred)

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
