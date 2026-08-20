from document.models import DocumentType
from document.validators import is_image_document_type
from rest_framework.permissions import BasePermission


class BackofficeDocumentPermission(BasePermission):
    message = "You do not have permission to manage backoffice documents."

    def has_permission(self, request, view):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request.user.has_perm("document.view_document")

        if request.method == "POST":
            return self._can_upload_document(request)

        if request.method == "PUT":
            return request.user.has_perm(
                "document.change_document"
            ) or request.user.has_perm("document.change_image_document")

        if request.method == "DELETE":
            return request.user.has_perm("document.delete_document")

        return False

    def has_object_permission(self, request, view, obj):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request.user.has_perm("document.view_document")

        if request.method == "PUT":
            return self._can_change_document(request, obj)

        if request.method == "DELETE":
            return request.user.has_perm("document.delete_document")

        return False

    def _can_upload_document(self, request):
        if request.user.has_perm("document.add_document"):
            return True

        return request.user.has_perm(
            "document.add_image_document"
        ) and is_image_document_type(self._request_document_type(request))

    def _can_change_document(self, request, obj):
        if request.user.has_perm("document.change_document"):
            return True

        current_document_type = getattr(obj, "document_type", None)
        requested_document_type = self._request_document_type(
            request,
            default=current_document_type,
        )

        return (
            request.user.has_perm("document.change_image_document")
            and is_image_document_type(current_document_type)
            and is_image_document_type(requested_document_type)
        )

    def _request_document_type(self, request, *, default=None):
        data = getattr(request, "data", {})
        if "document_type" not in data:
            return default

        try:
            return DocumentType.objects.get(
                pk=data.get("document_type"),
                is_active=True,
            )
        except (DocumentType.DoesNotExist, TypeError, ValueError):
            return None
