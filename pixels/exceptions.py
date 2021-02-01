class PixelsException(Exception):
    """
    Base exception for pixels.
    """

    pass


class TrainingDataParseError(PixelsException):
    """
    Error while parsing a training dataset.
    """

    pass
