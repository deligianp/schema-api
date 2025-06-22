import uuid as uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint, F

from api.constants import MountPointTypes, TaskStatus
from util.constraints import ApplicationUniqueConstraint
from util.decorators import update_fields
from util.defaults import get_current_datetime


@update_fields()
class Context(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=(not settings.USE_AUTH))
    name = models.CharField(max_length=255)

    class Meta:
        constraints = [
            ApplicationUniqueConstraint(
                fields=['name'],
                condition=Q(owner__isnull=True),
                name='context_name_unique',
                violation_error_message='Name is not available',
                error_context={'field': 'name'}
            ),
            ApplicationUniqueConstraint(
                fields=['name'],
                condition=Q(owner__isnull=False),
                name='context_name_unique_per_child',
                violation_error_message='Name is not available',
                error_context={'field': 'name'}
            )
        ]

    def __str__(self):
        return self.name


@update_fields()
class Participation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    context = models.ForeignKey(Context, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            ApplicationUniqueConstraint(
                fields=['user', 'context'],
                name='user_context_unique',
                violation_error_message='Referenced user is already a participant of the referenced context'
            )
        ]

    def __str__(self):
        return f'Participation of "{self.user.username}" in context "{self.context.name}"'


class Task(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    context = models.ForeignKey(Context, null=True, on_delete=models.SET_NULL)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        help_text='A unique UUID for identifying a task on this API',
        unique=True
    )
    backend_ref = models.CharField(
        help_text='Task ID that assigned to task by underlying API',
        max_length=255
    )
    manager_name = models.CharField(help_text='Manager name handling the execution', max_length=255)
    name = models.CharField(help_text='User-provided name', max_length=255)
    description = models.TextField(help_text='User-provided description')
    pending = models.BooleanField(
        default=True,
        help_text='A boolean field that indicates whether a task is still running; completed tasks won\'t poll the '
                  'underlying TESK API for the task status'
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp of task being approved and getting created'
    )

    # To be moved
    latest_update = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(
                    submitted_at__lt=F('latest_update'),
                ),
                name='update_after_task_submit'
            )
        ]

    @property
    def inputs(self):
        return self.mount_points.filter(is_input=True)

    @property
    def outputs(self):
        return self.mount_points.filter(is_input=False)


class StatusHistoryPoint(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='status_history_points')
    created_at = models.DateTimeField(default=get_current_datetime)
    status = models.IntegerField(choices=TaskStatus.choices)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(status__in=[choice.value for choice in TaskStatus]),
                name='status_history_enum'
            ),
        ]

    def __str__(self):
        return f'{self.task.uuid}: {TaskStatus(self.status).label}({self.created_at.isoformat()})'


# A model modified in such way that save() method is in effect only when it is the initial save of the instance
# It makes sense that certain (most) things in task requests are read-only after creation, since these things are
# configurations being used to spawn docker containers. Thus, an update on an instance of the corresponding DB relation
# would translate to more complex work needed to be done, if modifying the container was possible. In the context of
# this API, any task that is being accepted and created will have to either to die due to an error, get cancelled or
# complete successfully.
class Executor(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='executors')
    order = models.PositiveSmallIntegerField(help_text='Execution order of the executor')
    command = models.JSONField(help_text='JSON array-definition of the command to run inside the container')
    image = models.CharField(
        help_text='Docker image reference',
        max_length=255
    )
    stderr = models.CharField(
        help_text='Path to a file inside the container to which to dump stderr',
        max_length=255
    )
    stdin = models.CharField(
        help_text='Path to a file inside the container to read input from',
        max_length=255
    )
    stdout = models.CharField(
        help_text='Path to a file inside the container to which to dump stdout',
        max_length=255
    )
    workdir = models.CharField(
        blank=True,
        help_text='Path to a directory inside the container where the command will be executed',
        max_length=255
    )

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(image__regex=r'^\s*$'),
                name='image_not_empty'
            ),
            UniqueConstraint(
                fields=['task', 'order'],
                name='task_executor_order_unique'
            )
        ]


class Env(models.Model):
    executor = models.ForeignKey(Executor, on_delete=models.CASCADE, related_name='envs')
    key = models.CharField(
        help_text='Name of the container\'s environment variable (e.g. PATH for $PATH)',
        max_length=255
    )
    value = models.TextField(blank=True, help_text='Value of the container\'s environment variable')

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(key__regex=r'^\s*$'),
                name='env_key_not_empty',
            )
        ]


class MountPoint(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='mount_points')
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    url = models.CharField(
        help_text='Path to the file/directory, in the implemented filesystem',
        max_length=255
    )
    path = models.CharField(
        help_text='Path to the file/directory, in the container',
        max_length=255
    )
    type = models.CharField(choices=MountPointTypes.choices, max_length=10)
    is_input = models.BooleanField(
        default=True,
        help_text='Whether the file is an input file and should be located and mounted to the container during '
                  'initialization'
    )
    content = models.TextField(help_text='Input file content if url is not defined')

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(~Q(url__regex=r'^\s*$') | Q(type=MountPointTypes.FILE, is_input=True)),
                name='url_missing_only_if_is_file',
                violation_error_message=f'Given: url:{F("url")}, is_dir:{F("is_dir")}, is_input:{F("is_input")}'
            ),
            CheckConstraint(
                check=~Q(path__regex=r'^\s*$'),
                name='container_path_not_empty',
            ),
            CheckConstraint(
                check=Q(type__in=[choice[0] for choice in MountPointTypes.choices]),
                name='mountpoint_type_enum'
            )
        ]


class Volume(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='volumes')
    path = models.CharField(max_length=255)

    def __str__(self):
        return self.path

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(path__regex=r'^\s*$'),
                name='path_not_empty',
            )
        ]


class Tag(models.Model):
    tasks = models.ManyToManyField(Task, related_name='tags')
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['value'],
                name='tag_value_unique'
            ),
            CheckConstraint(
                check=~Q(value__regex=r'^\s*$'),
                name='tag_value_not_empty'
            )
        ]

class ResourceSet(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='resources')
    cpu_cores = models.IntegerField(default=settings.TASK_DEFAULT_RESOURCES['CPU'])
    ram_gb = models.FloatField(default=settings.TASK_DEFAULT_RESOURCES['RAM_GB'])
    disk_gb = models.FloatField(default=settings.TASK_DEFAULT_RESOURCES['DISK_GB'])
    preemptible = models.BooleanField(null=True)
    zones = models.JSONField(null=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(cpu_cores__gt=0),
                name='cpu_cores_min',
            ),
            CheckConstraint(
                check=Q(ram_gb__gte=0),
                name='ram_gb_min',
            ),
            CheckConstraint(
                check=Q(disk_gb__gte=0),
                name='disk_gb_min',
            )
        ]


class ExecutorOutputLog(models.Model):
    executor = models.OneToOneField(Executor, on_delete=models.CASCADE)
    stdout = models.TextField()
    stderr = models.TextField()
