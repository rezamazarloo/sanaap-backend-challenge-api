from rest_framework.permissions import BasePermission


class CanViewUser(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return request.user.has_perm("auth.view_user")


class CanCreateUser(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return request.user.has_perm("auth.add_user")


class CanViewGroup(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return request.user.has_perm("auth.view_group")


class CanAssignUserGroup(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return request.user.has_perm("auth.change_user")
