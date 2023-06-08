import secrets
from datetime import datetime
from typing import Tuple, Union

from cryptography.hazmat.primitives import hashes
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from api.models import Context, Participation
from api.services import ParticipationService
from api_auth.constants import AuthEntityType
from api_auth.models import UserProfile, ApiToken, AuthEntity
from util.datetime import parse_duration
from util.exceptions import ApplicationErrorHelper, ApplicationNotFoundError, ApplicationValidationError, \
    ApplicationError, ApplicationDuplicateError
from util.services import BaseService


# from knox.models import AuthToken


class AuthEntityService(BaseService):

    def __init__(self, parent: AuthEntity):
        if parent is not None and parent.entity_type != AuthEntityType.APPLICATION_SERVICE:
            raise ApplicationError('AuthEntityService parent must be an AuthEntity of type '
                                   f'"{AuthEntityType.APPLICATION_SERVICE}"')
        self.parent = parent

    # Utility protected methods

    @classmethod
    def _create_auth_entity(cls, *, username: str, entity_type: AuthEntityType, **optional):
        auth_entity = AuthEntity(username=username, entity_type=entity_type, **optional)
        try:
            auth_entity.full_clean()
        except ValidationError as ve:
            app_err = ApplicationErrorHelper.to_application_error(ve)
            raise app_err
        auth_entity.save()
        return auth_entity

    @classmethod
    def _get_auth_entities(cls) -> QuerySet[AuthEntity]:
        return AuthEntity.objects.all()

    @classmethod
    def _get_auth_entity(cls, *, username: str, parent: AuthEntity) -> AuthEntity:
        try:
            auth_entity = cls._get_auth_entities().get(username=username, parent=parent)
            return auth_entity
        except AuthEntity.DoesNotExist:
            raise ApplicationNotFoundError(f'No auth entity exists, for parent {parent} with username {username}')

    @classmethod
    def _update_auth_entity(cls, *, update_values: dict, auth_entity: AuthEntity = None, username: str = None,
                            parent: AuthEntity = None) -> AuthEntity:
        if not auth_entity:
            auth_entity = cls._get_auth_entity(username=username, parent=parent)

        auth_entity = cls._update_instance(auth_entity, **update_values)
        try:
            auth_entity.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        auth_entity.save()
        return auth_entity

    # Application service management methods

    @classmethod
    @transaction.atomic
    def create_application_service(cls, username: str) -> AuthEntity:
        return cls._create_auth_entity(username=username, entity_type=AuthEntityType.APPLICATION_SERVICE)

    @classmethod
    def get_application_services(cls) -> QuerySet[AuthEntity]:
        return cls._get_auth_entities().filter(entity_type=AuthEntityType.APPLICATION_SERVICE, parent=None)

    @classmethod
    def get_application_service(cls, username: str) -> AuthEntity:
        try:
            return cls.get_application_services().get(username=username)
        except AuthEntity.DoesNotExist:
            raise ApplicationNotFoundError(f'No application service exists with username "{username}"')

    @classmethod
    def update_application_service(cls, *, update_values: dict, auth_entity: AuthEntity = None,
                                   username: str = None) -> AuthEntity:
        if auth_entity is not None:
            if auth_entity.entity_type != AuthEntityType.APPLICATION_SERVICE:
                raise ApplicationValidationError(f'AuthEntity must be of type "{AuthEntityType.APPLICATION_SERVICE}"')
        else:
            auth_entity = cls.get_application_service(username)
        return cls._update_auth_entity(update_values=update_values, auth_entity=auth_entity)

    @classmethod
    def disable_application_service(cls, *, auth_entity: AuthEntity = None, username: str = None) -> AuthEntity:
        update_values = {
            'is_active': False
        }
        return cls.update_application_service(update_values=update_values, auth_entity=auth_entity, username=username)

    @classmethod
    def enable_application_service(cls, *, auth_entity: AuthEntity = None, username: str = None) -> AuthEntity:
        update_values = {
            'is_active': True
        }
        return cls.update_application_service(update_values=update_values, auth_entity=auth_entity, username=username)

    # Superuser management methods

    @classmethod
    @transaction.atomic
    def create_superuser(cls, username: str) -> AuthEntity:
        return cls._create_auth_entity(username=username, entity_type=AuthEntityType.USER, is_superuser=True)

    @classmethod
    def get_superusers(cls) -> QuerySet[AuthEntity]:
        return cls._get_auth_entities().filter(entity_type=AuthEntityType.USER, parent=None, is_superuser=True)

    @classmethod
    def get_superuser(cls, username: str) -> AuthEntity:
        try:
            return cls.get_superusers().get(username=username)
        except AuthEntity.DoesNotExist:
            raise ApplicationNotFoundError(f'No application service exists with username "{username}"')

    # User management methods

    @transaction.atomic
    def create_user(self, username: str, **optional) -> AuthEntity:
        user = self._create_auth_entity(username=username, entity_type=AuthEntityType.USER, parent=self.parent)

        # Retrieving related objects arguments
        profile_arguments = optional.pop('profile', {})
        if 'fs_user_dir' not in profile_arguments:
            profile_arguments['fs_user_dir'] = user.username

        user_profile_service = UserProfileService(user)
        user_profile_service.create_user_profile(**profile_arguments)

        return user

    def get_users(self) -> QuerySet[AuthEntity]:
        return self._get_auth_entities().filter(entity_type=AuthEntityType.USER, parent=self.parent)

    def get_user(self, username: str) -> AuthEntity:
        try:
            return self.get_users().get(username=username)
        except AuthEntity.DoesNotExist:
            raise ApplicationNotFoundError(f'No user exists with username "{username}"')

    def update_user(self, *, update_values: dict, auth_entity: AuthEntity = None, username: str = None) -> AuthEntity:
        if auth_entity is not None:
            if auth_entity.entity_type != AuthEntityType.USER or auth_entity.is_superuser:
                raise ApplicationError(f'Referenced user must be of type "{AuthEntityType.USER}" without superuser '
                                       f'privileges')
            elif auth_entity.parent != self.parent:
                raise ApplicationError('Referenced user must have the same parent as this service')
        else:
            auth_entity = self.get_user(username)

        profile_arguments = update_values.pop('profile', None)

        auth_entity = self._update_auth_entity(update_values=update_values, auth_entity=auth_entity)

        if profile_arguments:
            user_profile_service = UserProfileService(auth_entity)
            user_profile_service.update_user_profile(update_values=profile_arguments)

        return auth_entity

    def disable_user(self, *, auth_entity: AuthEntity = None, username: str = None) -> AuthEntity:
        update_values = {
            'is_active': False
        }
        return self.update_user(update_values=update_values, auth_entity=auth_entity, username=username)

    def enable_user(self, *, auth_entity: AuthEntity = None, username: str = None) -> AuthEntity:
        update_values = {
            'is_active': True
        }
        return self.update_user(update_values=update_values, auth_entity=auth_entity, username=username)

    def change_user_fs_dir(self, fs_user_dir: str, auth_entity: AuthEntity = None, username: str = None) -> AuthEntity:
        update_values = {
            'profile': {
                'fs_user_dir': fs_user_dir
            }
        }
        return self.update_user(update_values=update_values, auth_entity=auth_entity, username=username)


class UserProfileService(BaseService):

    def __init__(self, user: AuthEntity):
        if user.entity_type != AuthEntityType.USER:
            raise ApplicationError(f'UserProfileService\'s AuthEntity must be of type "{AuthEntityType.USER}"')
        self.user = user

    def _validate_fs_user_dir(self, fs_user_dir: str) -> None:
        parent = self.user.parent

        if fs_user_dir != '' and UserProfile.objects.filter(user__parent=parent, fs_user_dir=fs_user_dir).exists():
            raise ApplicationDuplicateError({'fs_user_dir': f'Provided {fs_user_dir} is not available'})

    def create_user_profile(self, *, fs_user_dir: str) -> UserProfile:
        self._validate_fs_user_dir(fs_user_dir=fs_user_dir)

        user_profile = UserProfile(user=self.user, fs_user_dir=fs_user_dir)
        try:
            user_profile.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        user_profile.save()
        return user_profile

    def update_user_profile(self, *, update_values: dict) -> UserProfile:
        if 'fs_user_dir' in update_values:
            self._validate_fs_user_dir(update_values['fs_user_dir'])
        user_profile = self.user.profile
        user_profile = self._update_instance(user_profile, **update_values)
        try:
            user_profile.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        user_profile.save()
        return user_profile


class ApiTokenService(BaseService):

    @staticmethod
    def authenticate(token: str) -> Union[Tuple[AuthEntity, None], Tuple[None, Participation]]:
        target_digest = ApiTokenService._hash_token(token)
        target_key = token[:settings.TOKEN_KEY_LENGTH]
        api_token = ApiToken.objects.filter(key=target_key, is_active=True, expiry__gt=timezone.now()).get(digest=target_digest)
        return api_token.auth_entity, api_token.participation

    def __init__(self, auth_entity: AuthEntity, context: Context = None):
        if context is None:
            self.auth_entity, self.participation = auth_entity, None
        else:
            participation_service = ParticipationService(context)
            self.auth_entity, self.participation = None, participation_service.get_participation(auth_entity)

    @staticmethod
    def _generate_token(n_bytes):
        return secrets.token_hex(n_bytes)

    @staticmethod
    def _hash_token(token):
        b_token = bytes.fromhex(token)
        hashing = hashes.Hash(hashes.SHA512())
        hashing.update(b_token)
        digest = hashing.finalize()
        return digest.hex()

    def _validate_expiry_after_timestamp(self, expiry: datetime, ts: datetime = timezone.now()):
        if expiry <= ts:
            raise ApplicationValidationError({'expiry': f'Expiry must be after "{ts}"'})

    def issue_token(self, **optional) -> Tuple[str, ApiToken]:
        token = ApiTokenService._generate_token(settings.TOKEN_BYTE_LENGTH)
        key = token[:settings.TOKEN_KEY_LENGTH]
        digest = ApiTokenService._hash_token(token)

        if 'expiry' not in optional:
            if 'duration' not in optional:
                raise ApplicationValidationError(
                    f'Either an `expiry` timestamp or a `duration` string must be provided for issuing an API token'
                )
            duration = optional['duration']
            try:
                dt = parse_duration(duration)
            except ValueError as ve:
                raise ApplicationValidationError({'duration': str(ve)})
            optional['created'] = timezone.now()
            optional['expiry'] = optional['created'] + dt
        optional.pop('duration', None)
        api_token = ApiToken(auth_entity=self.auth_entity, participation=self.participation, key=key, digest=digest,
                             **optional)
        try:
            api_token.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        api_token.save()
        return token, api_token

    def get_tokens(self) -> QuerySet[ApiToken]:
        return ApiToken.objects.filter(auth_entity=self.auth_entity, participation=self.participation)

    def get_token(self, token_uuid: str) -> ApiToken:
        try:
            return self.get_tokens().get(uuid=token_uuid)
        except ApiToken.DoesNotExist:
            raise ApplicationNotFoundError(f'No API token exists with uuid "{token_uuid}"')

    def update_token(self, *, update_values: dict, api_token: ApiToken = None, token_uuid: str = None):
        if not api_token:
            api_token = self.get_token(token_uuid)
        else:
            if api_token.auth_entity != self.auth_entity or api_token.participation != self.participation:
                raise ApplicationError('Referenced API token must authenticate the same entities as the '
                                       f'ApiTokenService (auth_entity: {str(self.auth_entity)}, '
                                       f'participation: {str(self.participation)})')

        if 'extend_duration' in update_values and 'expiry' not in update_values:
            try:
                dt = parse_duration(update_values['extend_duration'])
            except ValueError as ve:
                raise ApplicationValidationError({'extend_duration': str(ve)})
            update_values['expiry'] = api_token.expiry + dt

        if 'expiry' in update_values:
            # In the case of update, also check that new expiry will be after the current time
            self._validate_expiry_after_timestamp(update_values['expiry'], timezone.now())
        update_values.pop('extend_duration', None)

        api_token = ApiTokenService._update_instance(api_token, **update_values)
        try:
            api_token.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        api_token.save()
        return api_token

    def revoke_token(self, api_token: ApiToken = None, token_uuid: str = None):
        update_values = {
            'is_active': False
        }
        return self.update_token(update_values=update_values, api_token=api_token, token_uuid=token_uuid)
