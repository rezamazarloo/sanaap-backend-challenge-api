from types import SimpleNamespace
from unittest.mock import patch

from backoffice.document.permissions import (
    BackofficeDocumentAuditLogPermission,
    BackofficeDocumentPermission,
)
from django.test import SimpleTestCase


def make_user(pk, permissions=None):
    permissions = set(permissions or [])
    return SimpleNamespace(
        pk=pk,
        id=pk,
        has_perm=lambda permission: permission in permissions,
    )


def make_document_type(extensions, content_types=None):
    return SimpleNamespace(
        allowed_extensions=extensions,
        allowed_content_types=content_types or [],
    )


class BackofficeDocumentPermissionTests(SimpleTestCase):
    def setUp(self):
        self.permission = BackofficeDocumentPermission()
        self.document = SimpleNamespace(
            user_id=1,
            document_type=make_document_type(["pdf"]),
        )

    def test_view_permission_can_read_backoffice_documents(self):
        denied_request = SimpleNamespace(method="GET", user=make_user(2))
        allowed_request = SimpleNamespace(
            method="GET",
            user=make_user(2, permissions={"document.view_document"}),
        )

        self.assertFalse(self.permission.has_permission(denied_request, None))
        self.assertTrue(self.permission.has_permission(allowed_request, None))
        self.assertTrue(
            self.permission.has_object_permission(
                allowed_request,
                None,
                self.document,
            )
        )

    def test_add_permission_can_upload_any_document_type(self):
        request = SimpleNamespace(
            method="POST",
            user=make_user(2, permissions={"document.add_document"}),
            data={"document_type": "1"},
        )

        self.assertTrue(self.permission.has_permission(request, None))

    def test_image_add_permission_can_upload_image_document_type(self):
        request = SimpleNamespace(
            method="POST",
            user=make_user(2, permissions={"document.add_image_document"}),
            data={"document_type": "1"},
        )

        with patch(
            "backoffice.document.permissions.DocumentType.objects.get",
            return_value=make_document_type(["jpg", "png"]),
        ):
            self.assertTrue(self.permission.has_permission(request, None))

    def test_image_add_permission_cannot_upload_non_image_document_type(self):
        request = SimpleNamespace(
            method="POST",
            user=make_user(2, permissions={"document.add_image_document"}),
            data={"document_type": "1"},
        )

        with patch(
            "backoffice.document.permissions.DocumentType.objects.get",
            return_value=make_document_type(["pdf"]),
        ):
            self.assertFalse(self.permission.has_permission(request, None))

    def test_change_permission_can_update_any_document_type(self):
        request = SimpleNamespace(
            method="PUT",
            user=make_user(2, permissions={"document.change_document"}),
            data={"document_type": "1"},
        )

        self.assertTrue(self.permission.has_permission(request, None))
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.document)
        )

    def test_image_change_permission_can_update_image_to_image_document_type(self):
        request = SimpleNamespace(
            method="PUT",
            user=make_user(2, permissions={"document.change_image_document"}),
            data={"document_type": "2"},
        )
        document = SimpleNamespace(
            user_id=1,
            document_type=make_document_type(["jpg", "png"]),
        )

        with patch(
            "backoffice.document.permissions.DocumentType.objects.get",
            return_value=make_document_type(["webp"]),
        ):
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertTrue(
                self.permission.has_object_permission(request, None, document)
            )

    def test_image_change_permission_cannot_change_image_to_non_image_type(self):
        request = SimpleNamespace(
            method="PUT",
            user=make_user(2, permissions={"document.change_image_document"}),
            data={"document_type": "2"},
        )
        document = SimpleNamespace(
            user_id=1,
            document_type=make_document_type(["jpg", "png"]),
        )

        with patch(
            "backoffice.document.permissions.DocumentType.objects.get",
            return_value=make_document_type(["pdf"]),
        ):
            self.assertFalse(
                self.permission.has_object_permission(request, None, document)
            )

    def test_delete_requires_delete_permission(self):
        denied_request = SimpleNamespace(method="DELETE", user=make_user(2))
        allowed_request = SimpleNamespace(
            method="DELETE",
            user=make_user(2, permissions={"document.delete_document"}),
        )

        self.assertFalse(self.permission.has_permission(denied_request, None))
        self.assertTrue(self.permission.has_permission(allowed_request, None))
        self.assertTrue(
            self.permission.has_object_permission(
                allowed_request,
                None,
                self.document,
            )
        )


class BackofficeDocumentAuditLogPermissionTests(SimpleTestCase):
    def setUp(self):
        self.permission = BackofficeDocumentAuditLogPermission()

    def test_view_permission_can_read_document_audit_logs(self):
        denied_request = SimpleNamespace(method="GET", user=make_user(2))
        allowed_request = SimpleNamespace(
            method="GET",
            user=make_user(2, permissions={"document.view_documentauditlog"}),
        )

        self.assertFalse(self.permission.has_permission(denied_request, None))
        self.assertTrue(self.permission.has_permission(allowed_request, None))
