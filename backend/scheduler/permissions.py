from rest_framework.permissions import BasePermission


class IsDirector(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active and request.user.role == "director")
