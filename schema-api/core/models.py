from django.conf import settings
from django.db import models

import uuid

from api.constants import TaskStatus, MountPointTypes
from util.defaults import get_current_datetime


class BaseSchedulable(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True,
                            help_text='UUID reference to a schedulable')
    backend_ref = models.CharField(
        help_text='Backend reference ID assigned to a scheduled execution by underlying execution API',
        max_length=255
    )
    name = models.CharField(help_text='User-provided name', max_length=255, blank=True)
    description = models.TextField(help_text='User-provided description', blank=True)

    class Meta:
        abstract = True


class BaseStatus(models.Model):
    updated_at = models.DateTimeField(default=get_current_datetime)
    value = models.IntegerField(choices=TaskStatus.choices)

    class Meta:
        abstract = True

class BaseExecutionStateLog(models.Model):
    updated_at = models.DateTimeField(default=get_current_datetime)
    state = models.IntegerField(choices=TaskStatus.choices)

    class Meta:
        abstract = True


class BaseEnv(models.Model):
    key = models.CharField(
        help_text='Name of the container\'s environment variable (e.g. PATH for $PATH)',
        max_length=255
    )
    value = models.TextField(blank=True, help_text='Value of the container\'s environment variable')

    class Meta:
        abstract = True


class BaseExecutor(models.Model):
    command = models.JSONField(help_text='JSON array-definition of the command to run inside the container')
    image = models.CharField(
        help_text='Docker image reference',
        max_length=255
    )
    stderr = models.CharField(
        help_text='Path to a file inside the container to which to dump stderr',
        max_length=255,
        blank=True
    )
    stdin = models.CharField(
        help_text='Path to a file inside the container to read input from',
        max_length=255,
        blank=True
    )
    stdout = models.CharField(
        help_text='Path to a file inside the container to which to dump stdout',
        max_length=255,
        blank=True
    )
    workdir = models.CharField(
        blank=True,
        help_text='Path to a directory inside the container where the command will be executed',
        max_length=255
    )

    class Meta:
        abstract = True


class BaseMountPoint(models.Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    url = models.CharField(
        help_text='Path to the file/directory, in the implemented filesystem',
        max_length=255
    )
    path = models.CharField(
        help_text='Path to the file/directory, in the container',
        max_length=255
    )
    type = models.CharField(choices=MountPointTypes.choices, max_length=10)

    class Meta:
        abstract = True


class BaseInputMountPoint(BaseMountPoint):
    url = models.CharField(blank=True, max_length=255)
    content = models.TextField(help_text='Input file content if url is not defined', blank=True)

    class Meta:
        abstract = True


class BaseVolume(models.Model):
    path = models.CharField()

    class Meta:
        abstract = True


class BaseResourceSet(models.Model):
    cpu_cores = models.IntegerField(default=settings.TASK_DEFAULT_RESOURCES['CPU'])
    ram_gb = models.FloatField(default=settings.TASK_DEFAULT_RESOURCES['RAM_GB'])
    disk_gb = models.FloatField(default=settings.TASK_DEFAULT_RESOURCES['DISK_GB'])
    preemptible = models.BooleanField(null=True)
    zones = models.JSONField(null=True)

    class Meta:
        abstract = True


class BaseTag(models.Model):
    value = models.CharField(max_length=255)

    class Meta:
        abstract = True
