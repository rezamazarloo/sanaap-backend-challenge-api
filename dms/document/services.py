import logging
from uuid import uuid4

from django.db import transaction
from document.models import Document
from document.storage import ObjectStorage, ObjectStorageError, get_object_storage
from document.validators import ValidatedUpload

logger = logging.getLogger("document.services")


class DocumentService:
    def __init__(self, storage: ObjectStorage | None = None):
        self.storage = storage or get_object_storage()

    @property
    def download_expiration(self):
        return self.storage.default_expiration

    def upload_document(
        self,
        *,
        document_type,
        uploaded_file,
        user,
        uploaded_by,
        validated_upload: ValidatedUpload,
    ) -> Document:
        object_key = self._generate_object_key(
            user_id=user.pk,
            extension=validated_upload.extension,
        )

        uploaded_file.seek(0)
        self.storage.upload(
            object_key=object_key,
            file_obj=uploaded_file,
            size=validated_upload.size,
            content_type=validated_upload.content_type,
            metadata={
                "sha256": validated_upload.checksum,
                "user-id": str(user.pk),
                "uploaded-by": str(uploaded_by.pk),
            },
        )

        try:
            return Document.objects.create(
                document_type=document_type,
                user=user,
                original_filename=validated_upload.original_filename,
                object_key=object_key,
                content_type=validated_upload.content_type,
                size=validated_upload.size,
                checksum=validated_upload.checksum,
                uploaded_by=uploaded_by,
            )
        except Exception:
            self._rollback_uploaded_object(object_key)
            raise

    def delete_document(self, document: Document) -> None:
        self.storage.delete(document.object_key)
        document.delete()

    def replace_document(
        self,
        *,
        document: Document,
        document_type,
        uploaded_file,
        uploaded_by,
        validated_upload: ValidatedUpload,
    ) -> Document:
        old_object_key = document.object_key
        old_document_data = {
            "document_type": document.document_type,
            "original_filename": document.original_filename,
            "object_key": document.object_key,
            "content_type": document.content_type,
            "size": document.size,
            "checksum": document.checksum,
            "uploaded_by": document.uploaded_by,
        }
        new_object_key = self._generate_object_key(
            user_id=document.user_id,
            extension=validated_upload.extension,
        )

        uploaded_file.seek(0)
        self.storage.upload(
            object_key=new_object_key,
            file_obj=uploaded_file,
            size=validated_upload.size,
            content_type=validated_upload.content_type,
            metadata={
                "sha256": validated_upload.checksum,
                "user-id": str(document.user_id),
                "uploaded-by": str(uploaded_by.pk),
            },
        )

        try:
            with transaction.atomic():
                document.document_type = document_type
                document.original_filename = validated_upload.original_filename
                document.object_key = new_object_key
                document.content_type = validated_upload.content_type
                document.size = validated_upload.size
                document.checksum = validated_upload.checksum
                document.uploaded_by = uploaded_by
                document.save(
                    update_fields=[
                        "document_type",
                        "original_filename",
                        "object_key",
                        "content_type",
                        "size",
                        "checksum",
                        "uploaded_by",
                        "updated_at",
                    ]
                )
        except Exception:
            for field_name, value in old_document_data.items():
                setattr(document, field_name, value)
            self._rollback_uploaded_object(new_object_key)
            raise

        self._delete_replaced_object(old_object_key)
        return document

    def generate_download_url(self, document: Document) -> str:
        return self.storage.generate_download_url(
            object_key=document.object_key,
            expires_in=self.download_expiration,
            filename=document.original_filename,
            content_type=document.content_type,
        )

    def _generate_object_key(self, *, user_id, extension):
        return f"documents/{user_id}/{uuid4().hex}.{extension}"

    def _rollback_uploaded_object(self, object_key):
        try:
            self.storage.delete(object_key)
        except ObjectStorageError:
            logger.exception(
                "Failed to delete object '%s' after database creation failed.",
                object_key,
            )

    def _delete_replaced_object(self, object_key):
        try:
            self.storage.delete(object_key)
        except ObjectStorageError:
            logger.exception(
                "Failed to delete replaced object '%s'.",
                object_key,
            )
