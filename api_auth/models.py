import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Group, AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, UniqueConstraint, CheckConstraint, F
from django.utils import timezone

from api.models import Participation, Context
from api_auth.constants import AuthEntityType
from util.decorators import update_fields


@update_fields('is_active')
class AuthEntity(AbstractBaseUser):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    parent = models.ForeignKey('AuthEntity', on_delete=models.SET_NULL, null=True, blank=True)
    namespace_code = models.BigIntegerField(blank=True)
    username = models.SlugField(max_length=20)
    entity_type = models.CharField(max_length=32, choices=AuthEntityType.choices, default=AuthEntityType.USER)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    password = None

    contexts = models.ManyToManyField(to=Context, through=Participation, related_name='users')

    USERNAME_FIELD = 'uuid'

    class Meta:
        constraints = [
            UniqueConstraint('username', 'namespace_code', name='username_namespace_code_unique_together'),
            CheckConstraint(check=Q(username__regex=r'^[a-zA-Z][a-zA-Z0-9_]+$'), name='username_format'),
            CheckConstraint(check=Q(namespace_code__gte=0), name='namespace_code_value_domain'),
            CheckConstraint(check=Q(parent__isnull=True, namespace_code=0) | Q(parent=F('namespace_code')),
                            name='namespace_code_parent_relationship'),
            CheckConstraint(check=Q(entity_type__in=[_[0] for _ in AuthEntityType.choices]), name='entity_type__enum'),
            CheckConstraint(check=Q(namespace_code=0) | Q(is_superuser=False, entity_type=AuthEntityType.USER),
                            name='children_are_no_superuser_users'),
            CheckConstraint(check=~Q(entity_type=AuthEntityType.APPLICATION_SERVICE, is_superuser=True),
                            name='superuser_cannot_be_service')
        ]

    def __str__(self):
        return f'{self.entity_type} {self.username}'

    def save(self, *args, **kwargs):
        self.namespace_code = 0 if self.parent is None else self.parent.id
        super(AuthEntity, self).save(*args, **kwargs)


@update_fields('fs_user_dir')
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    fs_user_dir = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            CheckConstraint(check=~Q(fs_user_dir__regex=r'^\s*$'), name='fs_user_dir_not_empty')
        ]


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
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            CheckConstraint(check=
                            Q(auth_entity__isnull=False, participation__isnull=True) | Q(auth_entity__isnull=True,
                                                                                         participation__isnull=False),
                            name='token_authenticates_either_user_or_participation'),
            CheckConstraint(check=Q(created__lt=F('expiry')), name='expiry_after_creation',
                            violation_error_message='Token expiration date must be later than the creation date')
        ]
