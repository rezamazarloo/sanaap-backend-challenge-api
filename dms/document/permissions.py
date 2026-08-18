from rest_framework.permissions import BasePermission


class CanAddDocument(BasePermission):
    message = "You do not have permission to upload documents for users."

    def has_permission(self, request, view):
        return request.user.has_perm("document.add_document")


class CanViewDocuments(BasePermission):
    message = "You do not have permission to list all documents."

    def has_permission(self, request, view):
        return request.user.has_perm("document.view_document")


class DocumentPermission(BasePermission):
    message = "You do not have permission to access this document."

    def has_object_permission(self, request, view, obj):
        if obj.user_id == request.user.id:
            return True

        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request.user.has_perm("document.view_document")

        if request.method == "PUT":
            return request.user.has_perm("document.change_document")

        if request.method == "DELETE":
            return request.user.has_perm("document.delete_document")

        return False


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
