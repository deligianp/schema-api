from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from api.models import Task, Context
from util.defaults import get_current_datetime


# Create your models here.
class Experiment(models.Model):
    name = models.SlugField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=False)
    created_at = models.DateTimeField(default=get_current_datetime)
    context = models.ForeignKey(Context, on_delete=models.CASCADE)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    tasks = models.ManyToManyField(Task, blank=True)

    def clean(self):
        if self.description is None:
            raise ValidationError({'description': 'Description cannot be none'})

    class Meta:
        unique_together = (('name', 'creator', 'context'),)
