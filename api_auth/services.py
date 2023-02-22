import uuid
from datetime import timedelta, datetime
from typing import Tuple, Iterable

import django.contrib.auth.models
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import QuerySet, Q
from knox.models import AuthToken

from api.constants import TaskStatus
from api.models import Task
from api_auth.models import context_managers_group, ServiceProfile, ApiAuthToken


class AuthService:

    @staticmethod
    def get_context_managers() -> QuerySet:
        return context_managers_group.user_set.all()

    @staticmethod
    @transaction.atomic()
    def register_context_manager(username) -> Tuple[User, str]:
        user = User.objects.create_user(username)
        group = Group.objects.get(name='context_managers')
        user.groups.add(group)
        ServiceProfile.objects.create(service_data=user)
        _, auth_token = AuthToken.objects.create(user, expiry=timedelta(days=365))
        return user, auth_token

    @staticmethod
    def get_context_manager(username) -> User:
        return AuthService.get_context_managers().get(username=username)

    @staticmethod
    def get_context_manager_token(context_manager: User = None, username: str = None) -> str:
        if context_manager:
            auth_token = AuthToken.objects.get(user=context_manager)
        else:
            auth_token = AuthToken.objects.get(user__username=username)
        return auth_token.token_key

    @staticmethod
    def get_service_profile(user: User) -> ServiceProfile:
        return ServiceProfile.objects.get(service_data=user)


class ContextManagerService:

    def __init__(self, service_profile: ServiceProfile = None, context_manager=None, context_manager_name=None):
        self.service_profile = service_profile or \
                               ServiceProfile.objects.get(service_data=context_manager) or \
                               ServiceProfile.objects.get(service_data__username=context_manager_name)

    @transaction.atomic
    def register_context(self, context_name: str, limits_url: str) -> User:
        if not limits_url:
            limits_url = ''
        context = User.objects.create_user(username=context_name)
        group = Group.objects.get(name='contexts')
        context.groups.add(group)
        ServiceProfile.objects.create(service_data=context, context_manager_profile=self.service_profile,
                                      limits_url=limits_url)
        return context

    def get_contexts(self) -> QuerySet[django.contrib.auth.models.AbstractUser]:
        return User.objects.filter(profile__context_manager_profile=self.service_profile)

    def issue_context_token(self, context_name: str, title: str = None, expiry: datetime = None) -> str:
        if expiry and expiry < datetime.now(expiry.tzinfo):
            raise ValueError('Expiry timestamp of the API token must be in the future')
        context = self.get_contexts().get(username=context_name)
        _, token_str = ApiAuthToken.objects.create(context, title=title, expiry=expiry)
        return token_str

    @transaction.atomic
    def get_context_tokens(self, context_name: str) -> QuerySet:
        context = self.get_contexts().get(username=context_name)
        return ApiAuthToken.objects.filter(user__profile__context_manager_profile=self.service_profile, user=context)

    def get_active_context_tokens(self, context_name: str) -> QuerySet:
        return self.get_context_tokens(context_name).filter(expiry__gte=datetime.now())

    def get_expired_context_tokens(self, context_name: str) -> QuerySet:
        return self.get_context_tokens(context_name).filter(expiry__lt=datetime.now())

    def get_context_token(self, context_name: str, token_uuid: uuid.UUID) -> AuthToken:
        return self.get_context_tokens(context_name).get(uuid_ref=token_uuid)

    def update_context_token(self, username: str, token_uuid: uuid.UUID, **fields):
        update_fields = {'title', 'expiry'}
        acceptable_fields = {field: fields[field] for field in update_fields.intersection(set(fields.keys()))}
        return self.get_context_tokens(username).filter(uuid_ref=token_uuid).update(**acceptable_fields)

    def delete_context_token(self, username: str, token_uuid: uuid.UUID):
        self.get_context_token(username, token_uuid).delete()

    def get_context(self, context_name: str) -> django.contrib.auth.models.AbstractUser:
        return self.get_contexts().get(username=context_name)
