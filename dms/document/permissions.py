from document.models import DocumentType
from document.validators import is_image_document_type
from rest_framework.permissions import BasePermission


class CanViewDocuments(BasePermission):
    message = "You do not have permission to list all documents."

    def has_permission(self, request, view):
        return request.user.has_perm("document.view_document")


class DocumentPermission(BasePermission):
    message = "You do not have permission to access this document."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True

        if self._is_target_owner(request, view):
            return True

        return self._can_upload_document(request)

    def has_object_permission(self, request, view, obj):
        if self._is_owner(request, obj):
            return True

        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request.user.has_perm("document.view_document")

        if request.method == "PUT":
            return self._can_change_document(request, obj)

        if request.method == "DELETE":
            return request.user.has_perm("document.delete_document")

        return False

    def _is_owner(self, request, obj):
        return obj.user_id == request.user.id

    def _is_target_owner(self, request, view):
        target_user_id = getattr(view, "kwargs", {}).get("user_id", request.user.id)
        return str(target_user_id) == str(request.user.id)

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


class DocumentTypePermission(BasePermission):
    message = "You do not have permission to access this document type."
    permissions_by_method = {
        "GET": "document.view_documenttype",
        "HEAD": "document.view_documenttype",
        "OPTIONS": "document.view_documenttype",
        "POST": "document.add_documenttype",
        "PUT": "document.change_documenttype",
        "DELETE": "document.delete_documenttype",
    }

    def has_permission(self, request, view):
        permission = self.permissions_by_method.get(request.method)
        return permission is not None and request.user.has_perm(permission)
