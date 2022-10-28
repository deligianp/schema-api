import uuid as uuid
from django.db import models


# Create your models here.
class Task(models.Model):
    class TaskStatus(models.TextChoices):
        INITIALIZING = 'INITIALIZING'
        QUEUED = 'QUEUED'
        RUNNING = 'RUNNING'
        ERROR = 'ERROR'
        COMPLETED = 'COMPLETED'

    uuid = models.UUIDField(
        default=uuid.uuid4,
        help_text='A unique UUID for identifying a task on this API',
        unique=True
    )
    tesk_id = models.CharField(help_text='Task ID that TESK assigned to task', max_length=8, unique=True)
    name = models.CharField(help_text='User-provided name', max_length=50)
    description = models.CharField(help_text='User-provided description', max_length=200)
    pending = models.BooleanField(
        help_text='A boolean field that indicates whether a task is still running; completed tasks won\'t poll the '
                  'underlying TESK API for the task status'
    )
    status = models.CharField(
        choices=TaskStatus.choices,
        help_text='TESK API latest task status',
        max_length=30
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp of task being approved and getting created'
    )

    #
    command = models.JSONField(help_text='JSON array-definition of the command to run inside the container')
    image = models.CharField(
        help_text='Docker image reference',
        max_length=500
    )

    # TODO: require user definition - review when authentication is set up
    # Provide field(s) for sufficient user authentication for each task
    # user = None

    # TODO: require project name or other information, when authentication is set up
    # Project name
    # project = None

    # API address of TESK API
    # Note: The idea is that the TESK API address may change while tasks are still running on the old API. In addition,
    # multiple APIs may be available. For these reasons, it may be convenient to store the API related information,
    # so that tasks are retrievable
    # api_address = None
