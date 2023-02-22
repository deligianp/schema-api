import uuid as uuid

from django.db import models
from django.db.models import CheckConstraint, Q
from knox.models import User

from api.constants import TaskStatus, ErrorMessages
from util.decorators import not_updatable


class Task(models.Model):
    context = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        help_text='A unique UUID for identifying a task on this API',
        unique=True
    )
    task_id = models.CharField(
        help_text='Task ID that assigned to task by underlying API',
        max_length=50,
        unique=True,
        db_column='api_task_id'
    )
    name = models.CharField(help_text='User-provided name', max_length=50)
    description = models.TextField(help_text='User-provided description', blank=True)
    pending = models.BooleanField(
        default=True,
        help_text='A boolean field that indicates whether a task is still running; completed tasks won\'t poll the '
                  'underlying TESK API for the task status'
    )

    status = models.CharField(
        choices=TaskStatus.choices,
        default=TaskStatus.INITIALIZING,
        help_text='Task status',
        max_length=30
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp of task being approved and getting created'
    )

    # API address of TESK API
    # Note: The idea is that the TESK API address may change while tasks are still running on the old API. In addition,
    # multiple APIs may be available. For these reasons, it may be convenient to store the API related information,
    # so that tasks are retrievable
    address = models.URLField(
        help_text="Address to TESK API where task was delegated to and where its status can be retrieved from"
    )

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(task_id__regex=r'^\s*$'),
                name='task_id_not_empty',
                violation_error_message=ErrorMessages.TASK_TASK_ID_NOT_EMPTY_VIOLATION
            ),
            CheckConstraint(
                check=~Q(name__regex=r'^\s*$'),
                name='name_not_empty',
                violation_error_message=ErrorMessages.TASK_NAME_NOT_EMPTY_VIOLATION
            ),
            CheckConstraint(
                check=~Q(address__regex=r'^\s*$'),
                name='address_not_empty',
                violation_error_message=ErrorMessages.TASK_ADDRESS_NOT_EMPTY_VIOLATION
            ),
            CheckConstraint(
                check=Q(status__in=TaskStatus.values),
                name='status_enum',
                violation_error_message=ErrorMessages.TASK_STATUS_ENUM_VIOLATION
            )
        ]


# A model modified in such way that save() method is in effect only when it is the initial save of the instance
# It makes sense that certain (most) things in task requests are read-only after creation, since these things are
# configurations being used to spawn docker containers. Thus, an update on an instance of the corresponding DB relation
# would translate to more complex work needed to be done, if modifying the container was possible. In the context of
# this API, any task that is being accepted and created will have to either to die due to an error, get cancelled or
# complete successfully.
@not_updatable
class Executor(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='executors')
    # order = models.PositiveSmallIntegerField(help_text='Execution order of the executor')
    command = models.JSONField(help_text='JSON array-definition of the command to run inside the container')
    image = models.CharField(
        help_text='Docker image reference',
        max_length=500
    )
    stderr = models.CharField(
        default='/tmp/stderr',
        help_text='Path to a file inside the container to which to dump stderr',
        max_length=200
    )
    stdin = models.CharField(
        blank=True,
        help_text='Path to a file inside the container to read input from',
        max_length=200
    )
    stdout = models.CharField(
        default='/tmp/stdout',
        help_text='Path to a file inside the container to which to dump stdout',
        max_length=200
    )
    workdir = models.CharField(
        blank=True,
        help_text='Path to a directory inside the container where the command will be executed',
        max_length=200
    )

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(image__regex=r'^\s*$'),
                name='image_not_empty',
                violation_error_message=ErrorMessages.EXECUTOR_IMAGE_NOT_EMPTY_VIOLATION
            ),
            CheckConstraint(
                check=~Q(stderr__regex=r'^\s*$'),
                name='stderr_not_empty',
                violation_error_message=ErrorMessages.EXECUTOR_STDERR_NOT_EMPTY_VIOLATION
            ),
            CheckConstraint(
                check=~Q(stdout__regex=r'^\s*$'),
                name='stdout_not_empty',
                violation_error_message=ErrorMessages.EXECUTOR_STDOUT_NOT_EMPTY_VIOLATION
            ),
        ]


@not_updatable
class Env(models.Model):
    executor = models.ForeignKey(Executor, on_delete=models.CASCADE, related_name='envs')
    key = models.CharField(
        help_text='Name of the container\'s environment variable (e.g. PATH for $PATH)',
        max_length=50
    )
    value = models.TextField(blank=True, help_text='Value of the container\'s environment variable')

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(key__regex=r'^\s*$'),
                name='key_not_empty',
                violation_error_message=ErrorMessages.ENV_KEY_NOT_EMPTY_VIOLATION
            )
        ]


@not_updatable
class MountPoint(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='mount_points')
    filesystem_path = models.CharField(
        help_text='Path to the file/directory, in the implemented filesystem',
        max_length=200
    )
    container_path = models.CharField(
        help_text='Path to the file/directory, in the container',
        max_length=200
    )
    is_dir = models.BooleanField(default=False, help_text='Whether the path references a directory')
    is_input = models.BooleanField(
        default=True,
        help_text='Whether the file is an input file and should be located and mounted to the container during '
                  'initialization'
    )

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(container_path__regex=r'^\s*$'),
                name='container_path_not_empty',
                violation_error_message=ErrorMessages.MOUNTPOINT_CONTAINER_PATH_NOT_EMPTY_VIOLATION
            ),
            CheckConstraint(
                check=~Q(filesystem_path__regex=r'^\s*$'),
                name='filesystem_path_not_empty',
                violation_error_message=ErrorMessages.MOUNTPOINT_FILESYSTEM_PATH_NOT_EMPTY_VIOLATION
            )
        ]


@not_updatable
class Volume(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='volumes')
    path = models.CharField(max_length=200)

    def __str__(self):
        return self.path

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(path__regex=r'^\s*$'),
                name='path_not_empty',
                violation_error_message=ErrorMessages.VOLUME_PATH_NOT_EMPTY_VIOLATION
            )
        ]


@not_updatable
class Tag(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='tags')
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=50, blank=True)

# @not_updatable
# class ResourceSet(models.Model):
#     task = models.OneToOneField(Task, on_delete=models.CASCADE)
#     cpu_cores = models.IntegerField()
#     ram_gb = models.FloatField()
#     disk_gb = models.FloatField()
#
#     class Meta:
#         constraints = [
#             CheckConstraint(
#                 check=Q(cpu_cores__gt=0),
#                 name='cpu_cores_min',
#                 violation_error_message=ErrorMessages.RESOURCE_SET_CPU_CORES_MIN_VIOLATION
#             ),
#             CheckConstraint(
#                 check=Q(ram_gb__gte=1.0),
#                 name='ram_gb_min',
#                 violation_error_message=ErrorMessages.RESOURCE_SET_RAM_GB_MIN_VIOLATION
#             ),
#             CheckConstraint(
#                 check=Q(disk_gb__gte=30.0),
#                 name='disk_gb_min',
#                 violation_error_message=ErrorMessages.RESOURCE_SET_DISK_GB_MIN_VIOLATION
#             )
#         ]

# Following fields are defined in TES but are currently not used in the stack
# Implement them if these are also needed to be recorded and be used
# preemptible = None
# zones = None
