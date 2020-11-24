"""Pixels errors."""


class PixelsError(Exception):
    """Base error for Pixels."""

    status_code = 400

    def __init__(self, message, status_code=None, payload=None, tag=None):
        Exception.__init__(self)
        self.message = message
        self.tag = tag
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv

    def __str__(self):
        return self.message


class PixelsAuthenticationFailed(PixelsError):
    """Failed to authenticate on the pixels API."""
