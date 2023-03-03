import uuid as uuid

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint, F
from knox.models import User

from api.constants import TaskStatus, MountPointTypes


class Task(models.Model):
    context = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        help_text='A unique UUID for identifying a task on this API',
        unique=True
    )
    task_id = models.CharField(
        help_text='Task ID that assigned to task by underlying API',
        max_length=255,
        db_column='api_task_id'
    )
    name = models.CharField(help_text='User-provided name', max_length=255)
    description = models.TextField(help_text='User-provided description')
    pending = models.BooleanField(
        default=True,
        help_text='A boolean field that indicates whether a task is still running; completed tasks won\'t poll the '
                  'underlying TESK API for the task status'
    )

    status = models.CharField(
        choices=TaskStatus.choices,
        default=TaskStatus.SUBMITTED,
        help_text='Task status',
        max_length=30
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
                check=~Q(name__regex=r'^\s*$'),
                name='name_not_empty',
            ),
            CheckConstraint(
                check=Q(status__in=[choice[0] for choice in TaskStatus.choices]),
                name='status_enum'
            ),
            CheckConstraint(
                check=Q(~Q(task_id__regex=r'^\s*$') | Q(status=TaskStatus.SUBMITTED)),
                name='scheduled_task_task_id_required'
            ),
            CheckConstraint(
                check=Q(
                    Q(
                        Q(status=TaskStatus.CANCELED) | Q(status=TaskStatus.COMPLETED) |
                        Q(status=TaskStatus.ERROR), pending=False) |
                    Q(
                        ~Q(status=TaskStatus.CANCELED), ~Q(status=TaskStatus.COMPLETED),
                        ~Q(status=TaskStatus.ERROR), pending=True),
                ),
                name='task_status_is_pending_integrity_check'
            ),
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
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='tags')
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(key__regex=r'^\s*$'),
                name='tag_key_not_empty'
            )
        ]


class ResourceSet(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE)
    cpu_cores = models.IntegerField(null=True)
    ram_gb = models.FloatField(null=True)
    disk_gb = models.FloatField(null=True)
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
