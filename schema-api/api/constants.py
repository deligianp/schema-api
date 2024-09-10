from django.db import models


class _TaskStatus(models.IntegerChoices):
    UNKNOWN = -1, 'UNKNOWN'
    SUBMITTED = 0, 'SUBMITTED'
    APPROVED = 1, 'APPROVED'
    REJECTED = 2, 'REJECTED'
    SCHEDULED = 3, 'SCHEDULED'
    INITIALIZING = 4, 'INITIALIZING'
    RUNNING = 5, 'RUNNING'
    COMPLETED = 6, 'COMPLETED'
    ERROR = 7, 'ERROR'
    CANCELED = 8, 'CANCELED'


class MountPointTypes(models.TextChoices):
    FILE = 'FILE', 'FILE'
    DIRECTORY = 'DIRECTORY', 'DIRECTORY'


class ErrorMessages:
    VOLUME_PATH_NOT_EMPTY_VIOLATION = f'Volume path cannot be empty'
    MOUNTPOINT_FILESYSTEM_PATH_NOT_EMPTY_VIOLATION = f'Mountpoint filesystem path cannot be empty'
    MOUNTPOINT_CONTAINER_PATH_NOT_EMPTY_VIOLATION = f'Mountpoint container path cannot be empty'
    ENV_KEY_NOT_EMPTY_VIOLATION = f'Environment variable name cannot be empty'
    EXECUTOR_STDOUT_NOT_EMPTY_VIOLATION = f'Dump file path for stdout cannot be empty'
    EXECUTOR_STDERR_NOT_EMPTY_VIOLATION = f'Dump file path for stderr cannot be empty'
    TASK_ADDRESS_NOT_EMPTY_VIOLATION = f'Task API address cannot be empty'
    TASK_NAME_NOT_EMPTY_VIOLATION = f'Task name cannot be empty'
    TASK_TASK_ID_NOT_EMPTY_VIOLATION = f'Task API ID cannot be empty'
    EXECUTOR_IMAGE_NOT_EMPTY_VIOLATION = f'Image URI cannot be empty'
    RESOURCE_SET_CPU_CORES_MIN_VIOLATION = f'Number of CPU cores must be greater than 0'
    RESOURCE_SET_DISK_GB_MIN_VIOLATION = f'Amount of disk in GBs, must be at least 1GB'
    RESOURCE_SET_RAM_GB_MIN_VIOLATION = f'Amount of RAM in GBs, must be at least 1GB'
    TASK_STATUS_ENUM_VIOLATION = f'Task status must be any of the following ' \
                                 f'values: {", ".join(_[0] for _ in _TaskStatus.choices)}'
