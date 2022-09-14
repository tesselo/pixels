import numpy as np


def fill_missing_dimensions(tensor, expected_shape, value=None):
    """
    Fill a tensor with any shape (smaller dimensions than expected), with
    value to fill up until has the expected_shape dimensions.

    Parameters
    ----------
        tensor : numpy array
            Numpy array, X or Y object.
        expected_shape : tuple
            Shape to be expected to output on given dataset.
        value : int (float), optional
            Value to fill the gaps, defaults to zero.

    Returns
    -------
        tensor : numpy array
            Modified numpy array.

    """
    if not value and value != 0:
        value = 0
    missing_shape = tuple(x1 - x2 for (x1, x2) in zip(expected_shape, tensor.shape))
    for dim in range(len(tensor.shape)):
        current_shape = tensor.shape
        final_shape = np.array(current_shape)
        final_shape[dim] = missing_shape[dim]
        tensor = np.concatenate((tensor, np.full(tuple(final_shape), value)), axis=dim)
    return tensor


def multiclass_builder(Y, class_definition, max_number, y_nan_value=None):
    """
    Makes a linear array into a multiclass array.
    Takes the array Y, either a list or an integer.
    Parameters
    ----------
        Y : numpy array
            Goal image in training.
        class_definition : int or list
            Values to define the Y classes. If int is a number of classes, if a list it is the classes.
        max_number : float
            Maximum possible value on training data.
        y_nan_value : float
            NaN value for the image.
    Returns
    -------
        multiclass_y: numpy array
            Classified image.
    """
    nan_mask = Y == y_nan_value
    if isinstance(class_definition, int):
        # Linear division of value with class_definition classes.
        multiclass_y = Y / (max_number / class_definition)
        multiclass_y[multiclass_y > class_definition] = class_definition
        nan_class_value = class_definition
    else:
        class_number = 0
        class_definition = np.sort(np.unique(class_definition))
        multiclass_y = np.copy(Y)
        # Make brackets of classes.
        multiclass_y[Y <= class_definition[0]] = class_number
        for value in class_definition[1:]:
            down_value = class_definition[class_number]
            class_number += 1
            multiclass_y[np.logical_and(Y > down_value, Y <= value)] = class_number
        multiclass_y[Y > class_definition[-1]] = class_number + 1
        nan_class_value = class_number + 2
    # Make last class the nan_values.
    multiclass_y[nan_mask] = nan_class_value
    return multiclass_y.astype("int")


def class_sample_weights_builder(label, class_weights):
    # Create the image with the weights.
    return np.take(class_weights, label)
