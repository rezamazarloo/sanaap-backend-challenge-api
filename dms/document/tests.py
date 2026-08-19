from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils import timezone
from document.models import DocumentType
from document.pagination import DocumentPagination
from document.permissions import DocumentPermission
from document.serializers import AllDocumentListSerializer, DocumentListSerializer
from document.services import DocumentService
from document.storage import MinioStorage, build_attachment_content_disposition
from document.validators import UploadedFileValidator, ValidatedUpload
from document.views import AllDocumentListView, DocumentListCreateView

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 128


class FakeUser:
    def __init__(self, username):
        self.username = username

    def __str__(self):
        return self.username


class DocumentPaginationTests(SimpleTestCase):
    def test_document_pagination_defaults(self):
        self.assertEqual(DocumentPagination.page_size, 10)
        self.assertEqual(DocumentPagination.page_size_query_param, "page_size")
        self.assertEqual(DocumentPagination.max_page_size, 100)


class DocumentListFilterConfigTests(SimpleTestCase):
    def test_current_user_document_list_uses_drf_filter_backends(self):
        self.assertIn("document_type", DocumentListCreateView.filterset_fields)
        self.assertIn("document_type__code", DocumentListCreateView.filterset_fields)
        self.assertIn("content_type", DocumentListCreateView.filterset_fields)
        self.assertIn("created_at", DocumentListCreateView.filterset_fields)
        self.assertEqual(DocumentListCreateView.search_fields, ["original_filename"])
        self.assertIn("size", DocumentListCreateView.ordering_fields)

    def test_all_document_list_adds_owner_and_uploader_filters(self):
        self.assertIn("user", AllDocumentListView.filterset_fields)
        self.assertIn("uploaded_by", AllDocumentListView.filterset_fields)


class UploadedFileValidatorTests(SimpleTestCase):
    def setUp(self):
        self.document_type = DocumentType(
            name="Profile",
            code="profile",
            allowed_extensions=["png"],
            allowed_content_types=["image/png"],
            max_size_bytes=1024,
            is_active=True,
        )

    def test_validate_returns_server_detected_metadata_and_checksum(self):
        uploaded_file = SimpleUploadedFile(
            "avatar.png",
            PNG_BYTES,
            content_type="application/octet-stream",
        )

        result = UploadedFileValidator().validate(uploaded_file, self.document_type)

        self.assertEqual(result.original_filename, "avatar.png")
        self.assertEqual(result.extension, "png")
        self.assertEqual(result.content_type, "image/png")
        self.assertEqual(result.size, len(PNG_BYTES))
        self.assertEqual(len(result.checksum), 64)

    def test_validate_rejects_disguised_file(self):
        uploaded_file = SimpleUploadedFile(
            "avatar.png",
            b"not a png",
            content_type="image/png",
        )

        with self.assertRaises(ValidationError):
            UploadedFileValidator().validate(uploaded_file, self.document_type)


class ObjectStorageTests(SimpleTestCase):
    def test_build_attachment_content_disposition_supports_utf8_filename(self):
        header = build_attachment_content_disposition(
            "avatar \u0634\u0645\u0627\u0631\u0647.png"
        )

        self.assertIn("attachment", header)
        self.assertIn('filename="avatar .png"', header)
        self.assertIn(
            "filename*=UTF-8''avatar%20%D8%B4%D9%85%D8%A7%D8%B1%D9%87.png",
            header,
        )

    def test_minio_storage_uses_presign_client_for_download_urls(self):
        presign_client = FakePresignClient()
        storage = MinioStorage(
            client=SimpleNamespace(),
            presign_client=presign_client,
        )

        url = storage.generate_download_url(
            object_key="documents/42/avatar.png",
            expires_in=120,
            filename="avatar.png",
            content_type="image/png",
        )

        self.assertEqual(url, "http://localhost:9000/documents/42/avatar.png")
        self.assertEqual(presign_client.calls[0]["bucket_name"], "documents")
        self.assertEqual(
            presign_client.calls[0]["object_name"],
            "documents/42/avatar.png",
        )
        self.assertIn(
            "response-content-disposition",
            presign_client.calls[0]["response_headers"],
        )


class FakePresignClient:
    def __init__(self):
        self.calls = []

    def presigned_get_object(
        self,
        *,
        bucket_name,
        object_name,
        expires,
        response_headers=None,
    ):
        self.calls.append(
            {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "expires": expires,
                "response_headers": response_headers,
            }
        )
        return "http://localhost:9000/documents/42/avatar.png"


class FakeStorage:
    default_expiration = 300

    def __init__(self):
        self.uploaded_keys = []
        self.deleted_keys = []

    def upload(self, *, object_key, file_obj, size, content_type, metadata=None):
        self.uploaded_keys.append(object_key)

    def delete(self, object_key):
        self.deleted_keys.append(object_key)

    def generate_download_url(
        self,
        *,
        object_key,
        expires_in=None,
        filename=None,
        content_type=None,
    ):
        return f"https://storage.example/{object_key}"


class FakeDocument:
    def __init__(self):
        self.document_type = DocumentType(id=1, name="Old", code="old")
        self.original_filename = "old.png"
        self.object_key = "documents/42/old.png"
        self.content_type = "image/png"
        self.size = 10
        self.checksum = "0" * 64
        self.uploaded_by = type("User", (), {"pk": 1})()
        self.user_id = 42
        self.saved_update_fields = None
        self.fail_on_save = False

    def save(self, update_fields=None):
        if self.fail_on_save:
            raise RuntimeError("db down")
        self.saved_update_fields = update_fields


class DocumentServiceTests(SimpleTestCase):
    def test_upload_deletes_object_when_database_create_fails(self):
        storage = FakeStorage()
        service = DocumentService(storage=storage)
        uploaded_file = SimpleUploadedFile("avatar.png", PNG_BYTES)
        validated_upload = ValidatedUpload(
            original_filename="avatar.png",
            extension="png",
            content_type="image/png",
            size=len(PNG_BYTES),
            checksum="a" * 64,
        )
        user = type("User", (), {"pk": 42})()
        document_type = DocumentType(id=1, name="Profile", code="profile")

        with (
            patch("document.services.transaction.atomic", return_value=nullcontext()),
            patch(
                "document.services.Document.objects.create",
                side_effect=RuntimeError("db down"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                service.upload_document(
                    document_type=document_type,
                    uploaded_file=uploaded_file,
                    user=user,
                    uploaded_by=user,
                    validated_upload=validated_upload,
                )

        self.assertEqual(storage.deleted_keys, storage.uploaded_keys)

    def test_generate_object_key_uses_only_user_namespace(self):
        object_key = DocumentService(storage=FakeStorage())._generate_object_key(
            user_id=42,
            extension="png",
        )

        self.assertRegex(object_key, r"^documents/42/[a-f0-9]{32}\.png$")

    def test_replace_updates_document_and_deletes_previous_object(self):
        storage = FakeStorage()
        service = DocumentService(storage=storage)
        document = FakeDocument()
        old_object_key = document.object_key
        new_document_type = DocumentType(id=2, name="Profile", code="profile")
        uploaded_by = type("User", (), {"pk": 7})()
        validated_upload = ValidatedUpload(
            original_filename="new.png",
            extension="png",
            content_type="image/png",
            size=len(PNG_BYTES),
            checksum="b" * 64,
        )

        with patch("document.services.transaction.atomic", return_value=nullcontext()):
            result = service.replace_document(
                document=document,
                document_type=new_document_type,
                uploaded_file=SimpleUploadedFile("new.png", PNG_BYTES),
                uploaded_by=uploaded_by,
                validated_upload=validated_upload,
            )

        self.assertIs(result, document)
        self.assertEqual(document.document_type, new_document_type)
        self.assertEqual(document.original_filename, "new.png")
        self.assertEqual(document.content_type, "image/png")
        self.assertEqual(document.size, len(PNG_BYTES))
        self.assertEqual(document.checksum, "b" * 64)
        self.assertEqual(document.uploaded_by, uploaded_by)
        self.assertEqual(storage.deleted_keys, [old_object_key])
        self.assertEqual(storage.uploaded_keys, [document.object_key])
        self.assertIn("object_key", document.saved_update_fields)

    def test_replace_deletes_new_object_when_database_save_fails(self):
        storage = FakeStorage()
        service = DocumentService(storage=storage)
        document = FakeDocument()
        document.fail_on_save = True
        old_object_key = document.object_key
        old_filename = document.original_filename
        uploaded_by = type("User", (), {"pk": 7})()
        validated_upload = ValidatedUpload(
            original_filename="new.png",
            extension="png",
            content_type="image/png",
            size=len(PNG_BYTES),
            checksum="b" * 64,
        )

        with patch("document.services.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(RuntimeError):
                service.replace_document(
                    document=document,
                    document_type=DocumentType(id=2, name="Profile", code="profile"),
                    uploaded_file=SimpleUploadedFile("new.png", PNG_BYTES),
                    uploaded_by=uploaded_by,
                    validated_upload=validated_upload,
                )

        self.assertEqual(document.object_key, old_object_key)
        self.assertEqual(document.original_filename, old_filename)
        self.assertEqual(storage.deleted_keys, storage.uploaded_keys)


class PermissionUser:
    def __init__(self, user_id, permissions=None):
        self.id = user_id
        self.permissions = set(permissions or [])

    def has_perm(self, permission):
        return permission in self.permissions


class DocumentPermissionTests(SimpleTestCase):
    def setUp(self):
        self.permission = DocumentPermission()

    def test_owner_can_access_own_document(self):
        request = SimpleNamespace(method="PUT", user=PermissionUser(1))
        document = SimpleNamespace(user_id=1)

        self.assertTrue(self.permission.has_object_permission(request, None, document))

    def test_non_owner_needs_view_permission_to_read(self):
        request = SimpleNamespace(
            method="GET",
            user=PermissionUser(2, permissions={"document.view_document"}),
        )
        document = SimpleNamespace(user_id=1)

        self.assertTrue(self.permission.has_object_permission(request, None, document))

    def test_non_owner_needs_change_permission_to_update(self):
        request = SimpleNamespace(method="PUT", user=PermissionUser(2))
        document = SimpleNamespace(user_id=1)

        self.assertFalse(self.permission.has_object_permission(request, None, document))

        request.user.permissions.add("document.change_document")

        self.assertTrue(self.permission.has_object_permission(request, None, document))

    def test_non_owner_needs_delete_permission_to_delete(self):
        request = SimpleNamespace(method="DELETE", user=PermissionUser(2))
        document = SimpleNamespace(user_id=1)

        self.assertFalse(self.permission.has_object_permission(request, None, document))

        request.user.permissions.add("document.delete_document")

        self.assertTrue(self.permission.has_object_permission(request, None, document))


class DocumentSerializerTests(SimpleTestCase):
    def setUp(self):
        document_type = DocumentType(
            id=5,
            name="Profile",
            code="profile",
            description="Personal profile image.",
            allowed_extensions=["png"],
            allowed_content_types=["image/png"],
            max_size_bytes=1024,
            is_active=True,
        )
        self.document = SimpleNamespace(
            id=10,
            document_type=document_type,
            user=FakeUser("owner"),
            user_id=1,
            original_filename="avatar.png",
            content_type="image/png",
            size=136,
            checksum="c" * 64,
            uploaded_by=FakeUser("admin"),
            uploaded_by_id=2,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

    def test_current_user_document_serializer_is_compact(self):
        data = DocumentListSerializer(self.document).data

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "document_type",
                "original_filename",
                "content_type",
                "size",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(
            set(data["document_type"].keys()),
            {"id", "name", "code", "allowed_extensions", "max_size_bytes"},
        )

    def test_all_document_serializer_includes_admin_fields(self):
        data = AllDocumentListSerializer(self.document).data

        self.assertIn("checksum", data)
        self.assertIn("user", data)
        self.assertIn("user_id", data)
        self.assertIn("uploaded_by", data)
        self.assertIn("uploaded_by_id", data)
        self.assertIn("allowed_content_types", data["document_type"])
        self.assertIn("is_active", data["document_type"])
