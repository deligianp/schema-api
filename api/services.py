from typing import Iterable

from django.db import transaction

from api.constants import TaskStatus
from api.models import Task, Executor, Env, MountPoint, Volume, Tag
from api.taskapis import TesRuntime
from schema_api import settings


class ExecutorService:

    def __init__(self, executor: Executor = None, envs: Iterable[Env] = None, task=None):
        self.executor = executor
        if task is not None:
            self.executor.task = task
        self.envs = envs

        if self.envs is not None:
            for env in self.envs:
                env.executor = self.executor

    @transaction.atomic
    def save(self, validate: bool = True) -> Executor:
        if validate:
            self.full_clean()
            # self.executor.full_clean()
        self.executor.save()
        if self.envs is not None:
            for env in self.envs:
                env.save()
        return self.executor

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        self.executor.full_clean(exclude=exclude, validate_unique=validate_unique,
                                 validate_constraints=validate_constraints)
        if self.envs is not None:
            for env in self.envs:
                env.full_clean(exclude=['executor'], validate_unique=validate_unique,
                               validate_constraints=validate_constraints)


class TaskService:

    def __init__(self, task: Task = None, executors=None, mount_points=None, volumes=None, tags=None):
        self.task = task
        if len(executors) == 0:
            raise ValueError('At least one executor needs to be defined any task')
        self.executors = [ExecutorService(**executor_config, task=self.task) for executor_config in executors]
        if mount_points is not None:
            for mount_point in mount_points:
                mount_point.task = self.task
        self.mount_points = mount_points
        if volumes is not None:
            for volume in volumes:
                volume.task = self.task
        self.volumes = volumes
        if tags is not None:
            for tag in tags:
                tag.task = self.task
        self.tags = tags

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        self.task.full_clean(exclude=exclude)
        for executor in self.executors:
            executor.full_clean(exclude=['task'], validate_unique=validate_unique,
                                validate_constraints=validate_constraints)
        if self.mount_points is not None:
            for mount_point in self.mount_points:
                mount_point.full_clean(exclude=['task'], validate_unique=validate_unique,
                                       validate_constraints=validate_constraints)
        if self.volumes is not None:
            for volume in self.volumes:
                volume.full_clean(exclude=['task'], validate_unique=validate_unique,
                                  validate_constraints=validate_constraints)
        if self.tags is not None:
            for tag in self.tags:
                tag.full_clean(exclude=['task'], validate_unique=validate_unique,
                               validate_constraints=validate_constraints)

    @transaction.atomic
    def save(self, validate=True):
        # Validate
        if validate:
            self.full_clean(exclude=['task_id', 'address'])

        # Call resources API/database
        runtime = TesRuntime()
        # task_id = runtime.create_task(task=self.task, executors=self.executors, mount_points=self.mount_points,
        #                               volumes=self.volumes, tags=self.tags)
        task_id = runtime.create_task(task=self.task,
                                      executors_configurations=[
                                          {'executor': executor_config.executor, 'envs': executor_config.envs} for
                                          executor_config in self.executors], mount_points=self.mount_points,
                                      volumes=self.volumes, tags=self.tags)
        # Call runtime
        self.task.task_id = task_id
        self.task.address = runtime.get_endpoint
        self.task.save()
        for executor in self.executors:
            executor.save(validate=False)
        if self.mount_points is not None:
            for mount_point in self.mount_points:
                mount_point.save()
        if self.volumes is not None:
            for volume in self.volumes:
                volume.save()
        if self.tags is not None:
            for tag in self.tags:
                tag.save()

        return self.task

    @staticmethod
    def get_status(uuid):
        task = Task.objects.get(uuid=uuid)

        if task.pending:
            runtime = TesRuntime()
            status = runtime.get_task_by_id(task.task_id, task_api_get_endpoint=task.address)
            task.status = status
            if status not in (TaskStatus.INITIALIZING, TaskStatus.RUNNING):
                task.pending = False
            task.save()
        return task
