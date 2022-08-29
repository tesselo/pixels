import os
import pathlib
from urllib.parse import urlparse


class Path:
    def __init__(self, path: str):
        parts = urlparse(path)
        path = parts.path
        self.scheme = parts.scheme or None

        if parts.query:
            path += "?" + parts.query

        if parts.scheme and parts.netloc:
            path = parts.netloc + path

        parts = path.split("!")
        path = parts.pop() if parts else None
        self.archive = parts.pop() if parts else None
        self.path = pathlib.Path(path).as_posix()


def ensure_dirname(path):
    if path[-1] != os.path.sep:
        return f"{path}{os.path.sep}"
    return path
