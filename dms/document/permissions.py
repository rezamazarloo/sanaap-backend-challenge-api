from rest_framework.permissions import BasePermission


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
