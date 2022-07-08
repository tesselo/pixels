import glob
import json
import os
import zipfile
from io import BytesIO
from typing import Any, AnyStr, List

import h5py
import rasterio.path
import tensorflow as tf

from pixels.tio.s3 import S3


def is_archive(file_path: str) -> bool:
    """
    Checks if the file is an archive or if is contained in an archive.
    :param file_path: The file path.
    :return: True if the file is an archive, False otherwise.
    """
    return file_path.endswith(".zip") or file_path.startswith("zip")


def is_archive_parsed(parsed_path: Any) -> bool:
    """
    Checks if the parsed path is an archive.
    """
    return hasattr(parsed_path, "archive") and parsed_path.archive is not None


def is_dir(uri: str) -> bool:
    """
    Returns True if the uri is a directory.
    """
    if is_remote(uri):
        return len(uri.split(".")) == 1
    else:
        return os.path.isdir(uri)


def is_remote(uri: str) -> bool:
    """
    Returns True if the uri is a remote uri.
    """
    return uri.startswith("s3")


def file_exists(uri: str) -> bool:
    """
    Checks if the file exists locally or remotely.
    """
    if is_remote(uri):
        return S3(uri).file_exists()
    else:
        return os.path.exists(uri)


def list_files(uri: str, suffix: AnyStr) -> List[AnyStr]:
    """
    Returns a list of files in the directory or S3 bucket.
    """
    if is_remote(uri):
        return S3(uri).list(suffix=suffix)
    else:
        return glob.glob(f"{uri}/**/*{suffix}", recursive=True)


def get(uri: str) -> AnyStr:
    """
    Returns the file descriptor or local path of the file.
    """
    if is_remote(uri):
        return S3(uri).get()
    else:
        return uri


def read(uri: str, decode: bool = True, encoding: str = "utf-8") -> AnyStr:
    """
    Returns the content of a file.
    """
    if is_remote(uri):
        return S3(uri).open(decode, encoding)
    else:
        with open(uri, "r") as file:
            return file.read()


def write(uri: str, content) -> None:
    """
    Writes the content to a file.
    """
    if is_remote(uri):
        S3(uri).write(content)
    else:
        with open(uri, "w") as file:
            file.write(content)


def download(uri: str, destination: str) -> str:
    """
    Downloads a file from a local or remote uri to a local destination.
    """
    if is_remote(uri):
        return S3(uri).download(destination)
    else:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        os.rename(uri, destination)
        return destination


def upload(uri: str, suffix: str = "", delete_original=True) -> None:
    """
    Uploads a file to a specific location based on the uri.
    """
    S3(uri).upload(suffix, delete_original)


def load_dictionary(uri: str) -> dict:
    """
    Loads a dictionary from a file.
    """
    dictionary = json.loads(read(uri))
    return dictionary


def save_dictionary(uri: str, dictionary: dict) -> None:
    """
    Saves a dictionary to a file.
    """
    new_path = local_or_temp(uri)
    if not os.path.exists(new_path):
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
    with open(new_path, "w") as f:
        json.dump(dictionary, f)
    if is_remote(uri):
        upload(
            os.path.dirname(new_path),
            suffix=os.path.split(uri)[-1],
        )


def save_model(uri: str, model: tf.keras.Model):
    """
    Saves a model to a file.
    """
    if is_remote(uri):
        with BytesIO() as fl:
            with h5py.File(fl, mode="w") as h5fl:
                model.save(h5fl)
                h5fl.flush()
                h5fl.close()
            write(uri, fl.getvalue())
    else:
        with h5py.File(uri, mode="w") as h5fl:
            model.save(h5fl)


def local_or_temp(uri: str) -> str:
    """
    Returns the local path of a file or a temporary path.
    """
    if is_remote(uri):
        return uri.replace("s3://", "tmp/")
    return uri


def open_zip(parsed_path: rasterio.path.ParsedPath) -> zipfile.ZipFile:
    zip_file = get(parsed_path.archive)
    return zipfile.ZipFile(zip_file, "r")
