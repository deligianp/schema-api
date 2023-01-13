from rest_framework.permissions import BasePermission


class IsContextManager(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        return user.groups.filter(name='context_managers').exists()

class IsContext(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        return user.groups.filter(name='contexts').exists()
