from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from document.models import DocumentStatus, DocumentType
from document.services import DocumentService, DocumentStorageService
from document.validators import ValidatedUpload

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 128


def make_user(pk, permissions=None):
    permissions = set(permissions or [])
    return SimpleNamespace(
        pk=pk,
        id=pk,
        has_perm=lambda permission: permission in permissions,
    )


def make_validated_upload(filename="new.png", checksum="b" * 64):
    return ValidatedUpload(
        original_filename=filename,
        extension="png",
        content_type="image/png",
        size=len(PNG_BYTES),
        checksum=checksum,
    )


class FakeObjectStorage:
    default_expiration = 300

    def __init__(self):
        self.uploaded_keys = []
        self.deleted_keys = []

    def upload(self, *, object_key, file_obj, size, content_type, metadata=None):
        self.uploaded_keys.append(object_key)

    def delete(self, object_key):
        self.deleted_keys.append(object_key)

    def object_exists(self, object_key):
        return object_key in self.uploaded_keys

    def generate_download_url(self, **kwargs):
        return "https://storage.example/download"


class FakeDocument:
    pk = 123
    id = 123
    document_type = DocumentType(id=1, name="Old", code="old")
    original_filename = "new.png"
    object_key = "documents/42/new.png"
    content_type = "image/png"
    size = len(PNG_BYTES)
    checksum = "b" * 64
    status = DocumentStatus.PENDING
    uploaded_by_id = 7
    user_id = 42

    def __init__(self, local_file_path):
        self.local_file_path = local_file_path


class DocumentServiceTests(SimpleTestCase):
    def build_storage_service(self, local_storage_root):
        return DocumentStorageService(
            object_storage=FakeObjectStorage(),
            local_storage=FileSystemStorage(location=local_storage_root),
        )

    def test_staged_local_files_are_unique_and_under_documents_directory(self):
        with TemporaryDirectory() as local_storage_root:
            storage_service = self.build_storage_service(local_storage_root)
            first_path = storage_service.stage_uploaded_file(
                uploaded_file=SimpleUploadedFile("first.png", PNG_BYTES),
                object_key="documents/42/same-object.png",
            )
            second_path = storage_service.stage_uploaded_file(
                uploaded_file=SimpleUploadedFile("second.png", PNG_BYTES),
                object_key="documents/42/same-object.png",
            )

            self.assertTrue(first_path.startswith("documents/"))
            self.assertTrue(second_path.startswith("documents/"))
            self.assertTrue(storage_service.local_storage.exists(first_path))
            self.assertTrue(storage_service.local_storage.exists(second_path))
            self.assertNotEqual(first_path, second_path)

    def test_upload_stages_file_creates_pending_document_and_enqueues_on_commit(self):
        owner = make_user(42)

        with TemporaryDirectory() as local_storage_root:
            storage_service = self.build_storage_service(local_storage_root)
            callbacks = []
            document = SimpleNamespace(pk=123)

            with (
                patch(
                    "document.services.document.Document.objects.create",
                    return_value=document,
                ) as create,
                patch(
                    "document.services.document.transaction.atomic",
                    return_value=nullcontext(),
                ),
                patch(
                    "document.services.document.transaction.on_commit",
                    side_effect=callbacks.append,
                ),
                patch("document.services.document.AuditLogService.record"),
            ):
                result = DocumentService(
                    storage_service=storage_service
                ).upload_document(
                    document_type=DocumentType(id=1, name="Profile", code="profile"),
                    uploaded_file=SimpleUploadedFile("avatar.png", PNG_BYTES),
                    user=owner,
                    uploaded_by=owner,
                    validated_upload=make_validated_upload("avatar.png", "a" * 64),
                )

        self.assertIs(result, document)
        self.assertEqual(create.call_args.kwargs["status"], DocumentStatus.PENDING)
        self.assertTrue(create.call_args.kwargs["local_file_path"])
        self.assertEqual(len(callbacks), 1)

    def test_upload_deletes_local_file_when_database_create_fails(self):
        owner = make_user(42)

        with TemporaryDirectory() as local_storage_root:
            storage_service = self.build_storage_service(local_storage_root)

            with (
                patch(
                    "document.services.document.Document.objects.create",
                    side_effect=RuntimeError("db down"),
                ),
                patch(
                    "document.services.document.transaction.atomic",
                    return_value=nullcontext(),
                ),
                self.assertRaises(RuntimeError),
            ):
                DocumentService(storage_service=storage_service).upload_document(
                    document_type=DocumentType(id=1, name="Profile", code="profile"),
                    uploaded_file=SimpleUploadedFile("avatar.png", PNG_BYTES),
                    user=owner,
                    uploaded_by=owner,
                    validated_upload=make_validated_upload("avatar.png", "a" * 64),
                )

            staged_files = [
                path for path in Path(local_storage_root).rglob("*") if path.is_file()
            ]
            self.assertEqual(staged_files, [])

    def test_complete_pending_upload_verifies_object_marks_ready_and_deletes_local_file(
        self,
    ):
        with TemporaryDirectory() as local_storage_root:
            storage_service = self.build_storage_service(local_storage_root)
            local_file_path = storage_service.stage_uploaded_file(
                uploaded_file=SimpleUploadedFile("new.png", PNG_BYTES),
                object_key="documents/42/new.png",
            )
            document = FakeDocument(local_file_path)
            queryset = MagicMock()
            queryset.update.return_value = 1

            with (
                patch(
                    "document.services.document.Document.objects.get",
                    side_effect=[document, document],
                ),
                patch(
                    "document.services.document.Document.objects.filter",
                    return_value=queryset,
                ),
            ):
                DocumentService(
                    storage_service=storage_service
                ).complete_pending_upload(document.pk)

            self.assertFalse(storage_service.local_storage.exists(local_file_path))
            self.assertEqual(
                storage_service.object_storage.uploaded_keys,
                [document.object_key],
            )
            queryset.update.assert_called_once()
            self.assertEqual(
                queryset.update.call_args.kwargs["status"],
                DocumentStatus.READY,
            )
