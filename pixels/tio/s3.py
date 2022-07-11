import glob
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
        self.key = self.parsed.path[1:]
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
        except KeyError:
            raise PixelsException(
                f"Object not found in S3: {self.key} in {self.bucket}"
            )

    def write(self, data) -> None:
        obj = self.s3.Object(self.bucket, self.key)
        obj.put(Body=data)

    def list(self, suffix) -> List[AnyStr]:
        bucket = self.s3.Bucket(self.bucket)
        return [
            "s3://" + self.bucket + "/" + obj.key
            for obj in bucket.objects.filter(Prefix=self.key)
            if obj.key.endswith(suffix)
        ]

    def file_exists(self):
        return self.uri in self.list(suffix="")

    def upload(self, suffix: str, delete_original: bool) -> None:
        file_list = glob.glob(f"{self.uri}**/**/*{suffix}", recursive=True)
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
