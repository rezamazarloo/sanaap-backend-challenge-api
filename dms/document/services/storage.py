from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from document.models import Document
from document.storage import ObjectStorage, ObjectStorageError, get_object_storage


class LocalStagedFileMissing(Exception):
    pass


class DocumentStorageService:
    def __init__(
        self,
        *,
        object_storage: ObjectStorage | None = None,
        local_storage: FileSystemStorage | None = None,
    ):
        self.object_storage = object_storage or get_object_storage()
        self.local_storage = local_storage or FileSystemStorage(
            location=settings.DOCUMENT_LOCAL_STORAGE
        )

    @property
    def download_expiration(self):
        return self.object_storage.default_expiration

    def generate_object_key(self, *, user_id, extension):
        return f"documents/{user_id}/{uuid4().hex}.{extension}"

    def stage_uploaded_file(self, *, uploaded_file, object_key: str) -> str:
        extension = Path(object_key).suffix.lower()
        local_file_path = f"documents/{uuid4().hex}{extension}"

        uploaded_file.seek(0)
        saved_path = self.local_storage.save(local_file_path, uploaded_file)
        uploaded_file.seek(0)
        return saved_path

    def upload_staged_file(self, *, document_file, user_id, uploaded_by_id) -> None:
        if not self.local_file_exists(document_file.local_file_path):
            raise LocalStagedFileMissing("Local staged file is missing.")

        with self.local_storage.open(document_file.local_file_path, "rb") as file_obj:
            self.object_storage.upload(
                object_key=document_file.object_key,
                file_obj=file_obj,
                size=document_file.size,
                content_type=document_file.content_type,
                metadata={
                    "sha256": document_file.checksum,
                    "user-id": str(user_id),
                    "uploaded-by": str(uploaded_by_id),
                },
            )

        if not self.object_storage.object_exists(document_file.object_key):
            raise ObjectStorageError("Object upload verification failed.")

    def delete_local_file(self, local_file_path: str | None) -> None:
        if local_file_path and self.local_storage.exists(local_file_path):
            self.local_storage.delete(local_file_path)

    def local_file_exists(self, local_file_path: str | None) -> bool:
        return bool(local_file_path) and self.local_storage.exists(local_file_path)

    def delete_object(self, object_key: str) -> None:
        self.object_storage.delete(object_key)

    def generate_download_url(self, document: Document) -> str:
        return self.object_storage.generate_download_url(
            object_key=document.object_key,
            expires_in=self.download_expiration,
            filename=document.original_filename,
            content_type=document.content_type,
        )
