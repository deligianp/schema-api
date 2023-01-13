import uuid

from django.contrib.auth.models import Group, AbstractUser, UserManager
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

# Create your models here.
from django.db.models import Q
from knox.models import AuthToken, User, AuthTokenManager
from django.db import connection

required_tables = {'auth_user', 'auth_group', 'auth_user_groups'}
context_managers_group = None
contexts_group = None
if len(required_tables.difference(set(connection.introspection.table_names()))) == 0:
    context_managers_group, _ = Group.objects.get_or_create(name='context_managers')
    contexts_group, _ = Group.objects.get_or_create(name='contexts')

    content_types = ContentType.objects.all()
    context_managers_content_types = content_types.filter(
        Q(app_label='auth', model='User') | Q(app_label='knox', model='AuthToken') | Q(app_label='api_auth')
    )

    contexts_content_types = content_types.filter(
        Q(app_label='api')
    )


class ServiceProfileManager(models.Manager):

    def create(self, username, **kwargs):
        return super(ServiceProfileManager, self).create(**kwargs)


class ServiceProfile(models.Model):
    service_data = models.OneToOneField(User,
                                        help_text='User instance that holds auth-related information about the profile',
                                        on_delete=models.CASCADE, related_name='profile')
    context_manager_profile = models.ForeignKey('ServiceProfile',
                                                null=True,
                                                help_text='Reference to the context_name manager that registered this task '
                                                          'service',
                                                on_delete=models.CASCADE)


class ApiAuthTokenManager(AuthTokenManager):

    def create(self, user, title=None, expiry=None):
        with transaction.atomic():
            token, token_str = super(ApiAuthTokenManager, self).create(user=user)
            if title is None:
                title = token.token_key
            token.title = title
            if expiry:
                token.expiry = expiry
            token.save()
            return token, token_str


class ApiAuthToken(AuthToken):
    objects = ApiAuthTokenManager()

    title = models.CharField(max_length=255, help_text='Text that describes the use of the token')
    uuid_ref = models.UUIDField(unique=True,
                                default=uuid.uuid4,
                                help_text='A unique identifier for publicly referencing this API auth token')
