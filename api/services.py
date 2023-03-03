import uuid
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from api import taskapis
from api.constants import TaskStatus
from api.models import Task, Executor, Env, MountPoint, Volume, ResourceSet, Tag, ExecutorOutputLog


class TaskService:

    def __init__(self, context=None):
        self.context = context

    @transaction.atomic
    def submit_task(self, *, name: str, executors: Iterable[Executor], **optional):
        input_mount_points = optional.pop('inputs', None)
        output_mount_points = optional.pop('outputs', None)
        volumes = optional.pop('volumes', None)
        tags = optional.pop('tags', None)
        resource_set = optional.pop('resourceset', None)

        task = Task.objects.create(context=self.context, name=name, **optional)

        i = 0
        for executor in executors:
            envs = executor.pop('envs', None)

            i += 1
            order = i
            executor = Executor.objects.create(task=task, order=order, **executor)

            if envs:
                for kv_pair in envs:
                    Env.objects.create(executor=executor, key=kv_pair['key'], value=kv_pair['value'])

        if input_mount_points:
            for mount_point in input_mount_points:
                MountPoint.objects.create(task=task, is_input=True, **mount_point)
        if output_mount_points:
            for mount_point in output_mount_points:
                MountPoint.objects.create(task=task, is_input=False, **mount_point)
        if volumes:
            for volume_path in volumes:
                Volume.objects.create(task=task, path=volume_path)

        if resource_set:
            ResourceSet.objects.create(task=task, **resource_set)

        if tags:
            for kv_pair in tags:
                Tag.objects.create(task=task, **kv_pair)

        if settings.TASK_API:
            task_api_class = taskapis.get_task_api_class()
            task_api = task_api_class()

            task_id = task_api.create_task(task)

            task.task_id = task_id
            task.status = TaskStatus.SCHEDULED
            task.latest_update = timezone.now()
            task.save()
        return task

    @transaction.atomic
    def _check_if_update_task(self, task):
        if task.pending and \
                settings.TASK_API and \
                (task.latest_update - timezone.now()).seconds > settings.TASK_API['DB_TASK_STATUS_TTL_SECONDS']:
            task_api_class = taskapis.get_task_api_class()
            task_api = task_api_class()

            task_info = task_api.get_task_info(task.task_id)

            task_status = task_info['status']
            if task_status in [TaskStatus.COMPLETED, TaskStatus.ERROR, TaskStatus.CANCELED]:
                task.pending = False
            task.status = task_status

            executors_stderr = task_info['stderr']
            executors_stdout = task_info['stdout']
            n_executors_logged = len(executors_stdout)
            task_executors = task.executors.all().order_by('order')[:n_executors_logged].prefetch_related(
                'executoroutputlog'
            )
            for i in range(n_executors_logged):
                task_executor = task_executors[i]
                executor_stdout = executors_stdout[i]
                executor_stderr = executors_stderr[i]
                try:
                    executor_output_log = ExecutorOutputLog.objects.get(executor=task_executor)
                except ExecutorOutputLog.DoesNotExist:
                    executor_output_log = ExecutorOutputLog()
                executor_output_log.stdout = executor_stdout
                executor_output_log.stderr = executor_stderr
                executor_output_log.executor = task_executor
                executor_output_log.save()

            task.save()
        return task

    def get_task(self, task_uuid: uuid.UUID):
        task = Task.objects.get(context=self.context, uuid=task_uuid)

        task = self._check_if_update_task(task)

        return task

    def get_task_stdout(self, task_uuid: uuid.UUID):
        task = Task.objects.get(context=self.context, uuid=task_uuid)
        task = self._check_if_update_task(task)

        executors_stdout = [
            executor_output_log.stdout for executor_output_log in ExecutorOutputLog.objects.filter(executor__task=task)
        ]
        return executors_stdout

    def get_task_stderr(self, task_uuid: uuid.UUID):
        task = Task.objects.get(context=self.context, uuid=task_uuid)
        task = self._check_if_update_task(task)

        executors_stderr = [
            executor_output_log.stderr for executor_output_log in ExecutorOutputLog.objects.filter(executor__task=task)
        ]
        return executors_stderr

    def get_tasks(self):
        return Task.objects.filter(context=self.context)


class ContextService:

    @staticmethod
    def get_charged_tasks(context):
        context_tasks = Task.objects.filter(
            Q(status=TaskStatus.RUNNING) | Q(status=TaskStatus.COMPLETED),
            context=context)
        return context_tasks
