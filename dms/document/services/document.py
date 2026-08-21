from django.db import transaction
from django.utils import timezone
from document.models import Action, Document, DocumentStatus
from document.services.audit import AuditLogService
from document.services.storage import DocumentStorageService, LocalStagedFileMissing
from document.validators import ValidatedUpload
from rest_framework.exceptions import ValidationError


class DocumentService:
    def __init__(self, storage_service: DocumentStorageService | None = None):
        self.storage_service = storage_service or DocumentStorageService()

    @property
    def download_expiration(self):
        return self.storage_service.download_expiration

    def upload_document(
        self,
        *,
        document_type,
        uploaded_file,
        user,
        uploaded_by,
        validated_upload: ValidatedUpload,
    ) -> Document:
        object_key = self.storage_service.generate_object_key(
            user_id=user.pk,
            extension=validated_upload.extension,
        )
        local_file_path = self.storage_service.stage_uploaded_file(
            uploaded_file=uploaded_file,
            object_key=object_key,
        )

        try:
            with transaction.atomic():
                document = Document.objects.create(
                    document_type=document_type,
                    user=user,
                    original_filename=validated_upload.original_filename,
                    object_key=object_key,
                    local_file_path=local_file_path,
                    content_type=validated_upload.content_type,
                    size=validated_upload.size,
                    checksum=validated_upload.checksum,
                    status=DocumentStatus.PENDING,
                    uploaded_by=uploaded_by,
                )
                AuditLogService.record(
                    document=document,
                    action=Action.CREATED,
                    actor=uploaded_by,
                    metadata={
                        "filename": validated_upload.original_filename,
                        "document_type_id": document_type.pk,
                    },
                )
                transaction.on_commit(
                    lambda document_id=document.pk: self._enqueue_upload(document_id)
                )
        except Exception:
            self.storage_service.delete_local_file(local_file_path)
            raise

        return document

    def replace_document(
        self,
        *,
        document: Document,
        document_type,
        uploaded_file,
        uploaded_by,
        validated_upload: ValidatedUpload,
    ) -> Document:
        if document.status != DocumentStatus.READY:
            raise ValidationError(
                {"detail": "Only ready documents can be replaced."}
            )

        old_filename = document.original_filename
        old_checksum = document.checksum
        local_file_path = self.storage_service.stage_uploaded_file(
            uploaded_file=uploaded_file,
            object_key=document.object_key,
        )

        try:
            with transaction.atomic():
                document.document_type = document_type
                document.original_filename = validated_upload.original_filename
                document.local_file_path = local_file_path
                document.content_type = validated_upload.content_type
                document.size = validated_upload.size
                document.checksum = validated_upload.checksum
                document.status = DocumentStatus.PENDING
                document.uploaded_by = uploaded_by
                document.save(
                    update_fields=[
                        "document_type",
                        "original_filename",
                        "local_file_path",
                        "content_type",
                        "size",
                        "checksum",
                        "status",
                        "uploaded_by",
                        "updated_at",
                    ]
                )
                AuditLogService.record(
                    document=document,
                    action=Action.REPLACED,
                    actor=uploaded_by,
                    metadata={
                        "old_filename": old_filename,
                        "new_filename": validated_upload.original_filename,
                        "old_checksum": old_checksum,
                        "new_checksum": validated_upload.checksum,
                    },
                )
                transaction.on_commit(
                    lambda document_id=document.pk: self._enqueue_replacement(
                        document_id
                    )
                )
        except Exception:
            self.storage_service.delete_local_file(local_file_path)
            raise

        return document

    def complete_pending_upload(self, document_id: int) -> Document | None:
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            return None

        if document.status == DocumentStatus.READY:
            return document
        if document.status != DocumentStatus.PENDING:
            return document

        local_file_path = document.local_file_path
        try:
            self.storage_service.upload_staged_file(
                document_file=document,
                user_id=document.user_id,
                uploaded_by_id=document.uploaded_by_id,
            )
        except LocalStagedFileMissing:
            self.mark_document_upload_failed(document_id)
            return document

        updated = Document.objects.filter(
            pk=document_id,
            status=DocumentStatus.PENDING,
        ).update(
            status=DocumentStatus.READY,
            local_file_path="",
            updated_at=timezone.now(),
        )

        if updated:
            self.storage_service.delete_local_file(local_file_path)

        return Document.objects.get(pk=document_id)

    def complete_pending_replacement(self, document_id: int) -> Document | None:
        return self.complete_pending_upload(document_id)

    def delete_document(self, document: Document, *, actor) -> None:
        metadata = {
            "filename": document.original_filename,
            "object_key": document.object_key,
        }

        if document.status == DocumentStatus.READY:
            self.storage_service.delete_object(document.object_key)
        else:
            self.storage_service.delete_local_file(document.local_file_path)

        with transaction.atomic():
            AuditLogService.record(
                document=document,
                action=Action.DELETED,
                actor=actor,
                metadata=metadata,
            )
            document.delete()

    def generate_download_url(self, document: Document, *, actor) -> str:
        download_url = self.storage_service.generate_download_url(document)
        AuditLogService.record(
            document=document,
            action=Action.DOWNLOAD_LINK_GENERATED,
            actor=actor,
            metadata={"filename": document.original_filename},
        )
        return download_url

    def mark_document_upload_failed(self, document_id: int) -> None:
        Document.objects.filter(
            pk=document_id,
            status=DocumentStatus.PENDING,
        ).update(
            status=DocumentStatus.FAILED,
            updated_at=timezone.now(),
        )

    def enqueue_failed_upload_retries(self) -> dict[str, int]:
        from document.tasks import upload_document_task

        enqueued_documents = 0
        for document in (
            Document.objects.filter(status=DocumentStatus.FAILED)
            .exclude(local_file_path="")
            .only("id", "local_file_path")
        ):
            if not self.storage_service.local_file_exists(document.local_file_path):
                continue
            updated = Document.objects.filter(
                pk=document.pk,
                status=DocumentStatus.FAILED,
            ).update(
                status=DocumentStatus.PENDING,
                updated_at=timezone.now(),
            )
            if updated:
                upload_document_task.delay(document.pk)
                enqueued_documents += 1

        return {"documents": enqueued_documents}

    def _enqueue_upload(self, document_id: int) -> None:
        from document.tasks import upload_document_task

        upload_document_task.delay(document_id)

    def _enqueue_replacement(self, document_id: int) -> None:
        from document.tasks import replace_document_task

        replace_document_task.delay(document_id)
