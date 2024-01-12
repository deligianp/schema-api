from django.db import models
from django.utils.translation import gettext_lazy as _


class AuthEntityType(models.TextChoices):
    USER = "USER", _("User")
    APPLICATION_SERVICE = "APPLICATION_SERVICE", _("Application service")
