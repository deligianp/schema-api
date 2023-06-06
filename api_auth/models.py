import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Group, AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

from api.models import Participation, Context
from api_auth.constants import AuthEntityType
from util.constraints import ApplicationUniqueConstraint, ApplicationCheckConstraint
from util.decorators import update_fields


@update_fields('is_active')
class AuthEntity(AbstractBaseUser):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    parent = models.ForeignKey('AuthEntity', on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=20)
    entity_type = models.CharField(max_length=32, choices=AuthEntityType.choices, default=AuthEntityType.USER)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    password = None

    contexts = models.ManyToManyField(to=Context, through=Participation, related_name='users')

    USERNAME_FIELD = 'uuid'

    class Meta:
        constraints = [
            ApplicationUniqueConstraint(
                fields=['username', 'parent'],
                condition=Q(parent__isnull=False),
                name='username_parent_unique_together',
                violation_error_message='Username is not available',
                error_context={'field': 'username'}
            ),
            ApplicationUniqueConstraint(
                fields=['username'],
                condition=Q(parent__isnull=True),
                name='username_unique_when_no_parent',
                violation_error_message='Username is not available',
                error_context={'field': 'username'}
            ),
            ApplicationCheckConstraint(
                check=Q(username__regex='^' + settings.USERNAME_SLUG_PATTERN + '$'),
                name='username_format',
                violation_error_message=settings.USERNAME_SLUG_PATTERN_VIOLATION_MESSAGE,
                error_context={'field': 'username'}
            ),
            ApplicationCheckConstraint(
                check=Q(entity_type__in=[_[0] for _ in AuthEntityType.choices]),
                name='entity_type_enum',
                violation_error_message='Type must be either of the following values: '
                                        f'{", ".join(str(_[0]) for _ in AuthEntityType.choices)}',
                error_context={'field': 'entity_type'}
            ),
            ApplicationCheckConstraint(
                check=Q(parent__isnull=True) | Q(entity_type=AuthEntityType.USER),
                name='children_are_no_application_services',
                violation_error_message=f'Type cannot be {AuthEntityType.APPLICATION_SERVICE} when parent is not null',
                error_context={'field': 'entity_type'}
            ),
            ApplicationCheckConstraint(
                check=Q(parent__isnull=True) | Q(is_superuser=False),
                name='children_are_no_superusers',
                violation_error_message='Instance cannot represent a superuser when parent is not null',
                error_context={'field': 'is_superuser'}
            ),
            ApplicationCheckConstraint(
                check=~Q(entity_type=AuthEntityType.APPLICATION_SERVICE, is_superuser=True),
                name='application_services_cannot_be_superusers',
                violation_error_message='An application service cannot be a superuser',
                error_context={'field': 'is_superuser'}
            )
        ]

    def __str__(self):
        prefix = f'{self.entity_type} {self.username}'
        if self.parent:
            return prefix + f', managed by {self.parent.username}'
        return prefix


@update_fields('fs_user_dir')
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    fs_user_dir = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            ApplicationCheckConstraint(
                check=~Q(fs_user_dir__regex=r'^\s*$'),
                name='fs_user_dir_not_empty',
                violation_error_message='fs_user_dir cannot be empty',
                error_context={'field': 'fs_user_dir'}
            )
        ]

    def __str__(self):
        return f'{self.__class__.__name__}(fs_user_dir:{self.fs_user_dir})'


@update_fields('title', 'expiry', 'is_active')
class ApiToken(models.Model):
    auth_entity = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    participation = models.ForeignKey(Participation, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    key = models.CharField(max_length=settings.TOKEN_KEY_LENGTH, editable=False)
    digest = models.CharField(max_length=128, editable=False)
    created = models.DateTimeField(editable=False, default=timezone.now)
    expiry = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            ApplicationCheckConstraint(check=
                                       Q(auth_entity__isnull=False, participation__isnull=True) |
                                       Q(auth_entity__isnull=True, participation__isnull=False),
                                       name='token_authenticates_either_user_or_participation',
                                       violation_error_message='Either auth_entity should be null or participation '
                                                               'should be null'),
            ApplicationCheckConstraint(check=Q(created__lt=F('expiry')),
                                       name='expiry_after_creation',
                                       violation_error_message='Expiration date must be later than the creation date',
                                       error_context={'field': 'expiry'}
                                       )
        ]

    def __str__(self):
        return f'{self.__class__.__name__}({self.uuid}'
