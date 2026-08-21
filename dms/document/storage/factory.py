from functools import lru_cache

from document.storage.base import ObjectStorage
from document.storage.minio import MinioStorage


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    return MinioStorage()
