import os
import shutil
from typing import AnyStr, List
from urllib.parse import urlparse

import boto3

from pixels.const import REQUESTER_PAYS_BUCKETS
from pixels.exceptions import PixelsException


class S3:
    def __init__(self, uri: str):
        self.uri = uri
        self.s3 = boto3.resource("s3")
        self.parsed = urlparse(uri)
        self.bucket = self.parsed.netloc
        self.key = self.parsed.path.lstrip("/")
        self.requester_pays = (
            "requester" if self.bucket in REQUESTER_PAYS_BUCKETS else ""
        )

    def open(self, decode: bool, encoding: str):
        data = self.get().read()
        if decode:
            return data.decode(encoding)
        return data

    def get(self):
        try:
            return self.s3.Object(self.bucket, self.key).get(
                RequestPayer=self.requester_pays
            )["Body"]
        except (KeyError, self.s3.meta.client.exceptions.NoSuchKey):
            raise PixelsException(
                f"Object not found in S3: {self.key} in {self.bucket}"
            )

    def write(self, data) -> None:
        obj = self.s3.Object(self.bucket, self.key)
        obj.put(Body=data)

    def list(self, suffix) -> List[AnyStr]:
        paginator = self.s3.meta.client.get_paginator("list_objects_v2")
        paginated = paginator.paginate(Bucket=self.bucket, Prefix=self.key)

        all_objects = [ob["Contents"] for ob in paginated if "Contents" in ob]
        filtered_objects = []
        for object_group in all_objects:
            objs = [
                "s3://" + self.bucket + "/" + f["Key"]
                for f in object_group
                if f["Key"].endswith(suffix)
            ]
            filtered_objects += objs
        return filtered_objects

    def file_exists(self):
        return self.uri in self.list(suffix="")

    def upload(self, file_list: List[str], delete_original: bool) -> None:
        base_dir, bucket, *_ = self.uri.split("/")
        local_start = f"{base_dir}/{bucket}/"

        for file in file_list:
            key_path = file.replace(local_start, "", 1)
            self.s3.meta.client.upload_file(file, bucket, key_path)

        if delete_original:
            if base_dir in ["/", "root", ""]:
                raise PixelsException(
                    "Refusing to delete potentially dangerous directories"
                )
            shutil.rmtree(base_dir)

    def download(self, directory: str) -> str:
        save_path = os.path.join(directory, self.key)
        if not os.path.exists(save_path):
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
        bucket = self.s3.Bucket(self.bucket)
        bucket.download_file(self.key, save_path)
        return save_path
