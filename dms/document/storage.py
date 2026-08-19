from abc import ABC, abstractmethod
from datetime import timedelta
from functools import lru_cache
from threading import Lock
from typing import BinaryIO
from urllib.parse import quote

from django.conf import settings
from minio import Minio
from minio.error import InvalidResponseError, MinioException, S3Error, ServerError


class ObjectStorageError(Exception):
    pass


class ObjectStorage(ABC):
    @property
    @abstractmethod
    def default_expiration(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def upload(
        self,
        *,
        object_key: str,
        file_obj: BinaryIO,
        size: int,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, object_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate_download_url(
        self,
        *,
        object_key: str,
        expires_in: int | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> str:
        raise NotImplementedError


class MinioClientFactory:
    _client = None
    _presign_client = None
    _lock = Lock()
    _presign_lock = Lock()

    @classmethod
    def get_client(cls) -> Minio:
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    minio_config = settings.MINIO
                    cls._client = cls._build_client(
                        endpoint=minio_config["endpoint"],
                        secure=minio_config["secure"],
                    )

        return cls._client

    @classmethod
    def get_presign_client(cls) -> Minio:
        minio_config = settings.MINIO
        public_endpoint = minio_config.get("public_endpoint")
        if not public_endpoint:
            return cls.get_client()

        if cls._presign_client is None:
            with cls._presign_lock:
                if cls._presign_client is None:
                    cls._presign_client = cls._build_client(
                        endpoint=public_endpoint,
                        secure=minio_config["public_secure"],
                    )

        return cls._presign_client

    @classmethod
    def _build_client(cls, *, endpoint: str, secure: bool) -> Minio:
        minio_config = settings.MINIO
        return Minio(
            endpoint=endpoint,
            access_key=minio_config["access_key"],
            secret_key=minio_config["secret_key"],
            secure=secure,
            region=minio_config["region"],
        )


class MinioStorage(ObjectStorage):
    def __init__(
        self,
        client: Minio | None = None,
        presign_client: Minio | None = None,
    ):
        minio_config = settings.MINIO
        self.client = client or MinioClientFactory.get_client()
        self.presign_client = presign_client or MinioClientFactory.get_presign_client()
        self.bucket = minio_config["bucket"]
        self._default_expiration = minio_config["presigned_url_expiration"]
        self._bucket_ready = False
        self._bucket_lock = Lock()

    @property
    def default_expiration(self) -> int:
        return self._default_expiration

    def upload(
        self,
        *,
        object_key: str,
        file_obj: BinaryIO,
        size: int,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self._ensure_private_bucket()

        try:
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_key,
                data=file_obj,
                length=size,
                content_type=content_type,
                metadata=metadata,
            )
        except (InvalidResponseError, MinioException, S3Error, ServerError) as exc:
            raise ObjectStorageError("Could not upload object to storage.") from exc

    def delete(self, object_key: str) -> None:
        try:
            self.client.remove_object(self.bucket, object_key)
        except (InvalidResponseError, MinioException, S3Error, ServerError) as exc:
            raise ObjectStorageError("Could not delete object from storage.") from exc

    def generate_download_url(
        self,
        *,
        object_key: str,
        expires_in: int | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> str:
        response_headers = {}
        if filename:
            response_headers["response-content-disposition"] = (
                build_attachment_content_disposition(filename)
            )
        if content_type:
            response_headers["response-content-type"] = content_type

        try:
            return self.presign_client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_key,
                expires=timedelta(seconds=expires_in or self.default_expiration),
                response_headers=response_headers or None,
            )
        except (InvalidResponseError, MinioException, S3Error, ServerError) as exc:
            raise ObjectStorageError("Could not generate download URL.") from exc

    def _ensure_private_bucket(self):
        if self._bucket_ready:
            return

        with self._bucket_lock:
            if self._bucket_ready:
                return

            try:
                if not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
                self._delete_bucket_policy_if_present()
            except (InvalidResponseError, MinioException, S3Error, ServerError) as exc:
                raise ObjectStorageError("Could not prepare storage bucket.") from exc

            self._bucket_ready = True

    def _delete_bucket_policy_if_present(self):
        try:
            self.client.delete_bucket_policy(self.bucket)
        except S3Error as exc:
            if exc.code not in {"NoSuchBucketPolicy", "NoSuchPolicy"}:
                raise


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    return MinioStorage()


def build_attachment_content_disposition(filename: str) -> str:
    sanitized_filename = filename.replace("\r", "").replace("\n", "")
    quoted_filename = quote(sanitized_filename, safe="")
    ascii_filename = (
        sanitized_filename.encode("ascii", "ignore")
        .decode("ascii")
        .replace("\\", "\\\\")
        .replace('"', r"\"")
    )

    if ascii_filename:
        return (
            f'attachment; filename="{ascii_filename}"; '
            f"filename*=UTF-8''{quoted_filename}"
        )

    return f"attachment; filename*=UTF-8''{quoted_filename}"
