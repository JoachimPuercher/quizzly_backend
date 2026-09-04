from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Grant object access only to the user who owns the quiz."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
