from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from document.models import DocumentType
from document.services import DocumentService
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


class FakeStorage:
    default_expiration = 300

    def __init__(self):
        self.uploaded_keys = []
        self.deleted_keys = []

    def upload(self, *, object_key, file_obj, size, content_type, metadata=None):
        self.uploaded_keys.append(object_key)

    def delete(self, object_key):
        self.deleted_keys.append(object_key)


class FakeDocument:
    def __init__(self):
        self.document_type = DocumentType(id=1, name="Old", code="old")
        self.original_filename = "old.png"
        self.object_key = "documents/42/old.png"
        self.content_type = "image/png"
        self.size = 10
        self.checksum = "0" * 64
        self.uploaded_by = make_user(1)
        self.user_id = 42
        self.fail_on_save = False

    def save(self, update_fields=None):
        if self.fail_on_save:
            raise RuntimeError("db down")


class DocumentServiceTests(SimpleTestCase):
    def test_upload_deletes_object_when_database_create_fails(self):
        storage = FakeStorage()
        owner = make_user(42)

        with (
            patch(
                "document.services.Document.objects.create",
                side_effect=RuntimeError("db down"),
            ),
            self.assertRaises(RuntimeError),
        ):
            DocumentService(storage=storage).upload_document(
                document_type=DocumentType(id=1, name="Profile", code="profile"),
                uploaded_file=SimpleUploadedFile("avatar.png", PNG_BYTES),
                user=owner,
                uploaded_by=owner,
                validated_upload=make_validated_upload("avatar.png", "a" * 64),
            )

        self.assertEqual(storage.deleted_keys, storage.uploaded_keys)

    def test_replace_updates_document_and_deletes_previous_object(self):
        storage = FakeStorage()
        document = FakeDocument()
        old_object_key = document.object_key
        uploaded_by = make_user(7)

        with patch("document.services.transaction.atomic", return_value=nullcontext()):
            result = DocumentService(storage=storage).replace_document(
                document=document,
                document_type=DocumentType(id=2, name="Profile", code="profile"),
                uploaded_file=SimpleUploadedFile("new.png", PNG_BYTES),
                uploaded_by=uploaded_by,
                validated_upload=make_validated_upload(),
            )

        self.assertIs(result, document)
        self.assertEqual(document.original_filename, "new.png")
        self.assertEqual(document.content_type, "image/png")
        self.assertEqual(document.size, len(PNG_BYTES))
        self.assertEqual(document.checksum, "b" * 64)
        self.assertEqual(document.uploaded_by, uploaded_by)
        self.assertEqual(storage.uploaded_keys, [document.object_key])
        self.assertEqual(storage.deleted_keys, [old_object_key])

    def test_replace_deletes_new_object_when_database_save_fails(self):
        storage = FakeStorage()
        document = FakeDocument()
        document.fail_on_save = True
        old_object_key = document.object_key

        with (
            patch("document.services.transaction.atomic", return_value=nullcontext()),
            self.assertRaises(RuntimeError),
        ):
            DocumentService(storage=storage).replace_document(
                document=document,
                document_type=DocumentType(id=2, name="Profile", code="profile"),
                uploaded_file=SimpleUploadedFile("new.png", PNG_BYTES),
                uploaded_by=make_user(7),
                validated_upload=make_validated_upload(),
            )

        self.assertEqual(document.object_key, old_object_key)
        self.assertEqual(storage.deleted_keys, storage.uploaded_keys)
