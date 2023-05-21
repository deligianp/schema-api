from rest_framework.permissions import BasePermission

from api.models import Participation, Context
from api.services import ParticipationService
from api_auth.models import AuthEntity
from api_auth.constants import AuthEntityType


class IsUser(BasePermission):

    def has_permission(self, request, view):
        user: AuthEntity = request.user
        return user.entity_type == AuthEntityType.USER


class IsApplicationService(BasePermission):

    def has_permission(self, request, view):
        user: AuthEntity = request.user
        return user.entity_type == AuthEntityType.APPLICATION_SERVICE


class IsActive(BasePermission):

    def has_permission(self, request, view):
        user: AuthEntity = request.user
        is_active = True
        if user.entity_type == AuthEntityType.USER:
            is_active &= (user.parent is None or user.parent.is_active)
        is_active &= user.is_active
        return is_active


class IsContextMember(BasePermission):

    def has_permission(self, request, view):
        user: AuthEntity = request.user
        try:
            context: Context = request.context
        except AttributeError:
            return False

        try:
            ParticipationService(context=context).get_participation(user)
        except Participation.DoesNotExist:
            raise False
        return True
