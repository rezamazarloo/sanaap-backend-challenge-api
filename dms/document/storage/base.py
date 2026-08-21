from abc import ABC, abstractmethod
from typing import BinaryIO


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
    def object_exists(self, object_key: str) -> bool:
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
