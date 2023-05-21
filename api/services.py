import uuid
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from api import taskapis
from api.constants import TaskStatus
from api.models import Task, Executor, Env, MountPoint, Volume, ResourceSet, Tag, ExecutorOutputLog, Context, \
    Participation, ContextQuotas
from api_auth.models import AuthEntity
from api_auth.constants import AuthEntityType
from util.services import BaseService


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


class ParticipationService:

    def __init__(self, context: Context):
        self.context = context

    def add_to_context(self, user: AuthEntity) -> Participation:
        if user.entity_type != AuthEntityType.USER:
            raise TypeError(f'Only {AuthEntityType.USER} type AuthEntities can be added to a context')

        if user.parent != self.context.owner:
            raise ValueError(f'Referenced user\'s parent is different from the context\'s application service')

        participation = Participation(user=user, context=self.context)
        participation.full_clean()
        participation.save()
        return participation

    def get_participations(self) -> QuerySet[Participation]:
        return Participation.objects.filter(context=self.context)

    def get_participation(self, auth_entity: AuthEntity) -> Participation:
        return self.get_participations().get(user=auth_entity)

    def remove_from_context(self, user: AuthEntity):
        participation = Participation.objects.get(user=user, context=self.context)
        participation.delete()


class ContextService:

    def __init__(self, application_service: AuthEntity):
        if application_service.entity_type != AuthEntityType.APPLICATION_SERVICE:
            raise TypeError(
                f'{type(self).__name__} depends on a User object of'
                f' type {AuthEntityType.APPLICATION_SERVICE}. Given: {application_service.entity_type}'
            )

        self.application_service = application_service

    @transaction.atomic
    def create_context(self, *, name: str, **optional):
        quotas = optional.pop('quotas', {})

        # slugify name?

        context = Context(owner=self.application_service, name=name)
        context.full_clean()
        context.save()

        context_quotas_service = ContextQuotasService(context)
        context_quotas_service.create_context_quotas(**quotas)

        return context

    def get_contexts(self) -> QuerySet:
        return Context.objects.filter(owner=self.application_service)

    def get_context(self, *, name: str) -> Context:
        return self.get_contexts().get(name=name)

    @transaction.atomic
    def update_context(self, *, update_values: dict, context: Context = None, name: str = None) -> Context:
        if not context:
            context = self.get_context(name=name)
        else:
            if context.owner != self.application_service:
                raise ValueError(f'Referenced context is owned by a different {AuthEntityType.APPLICATION_SERVICE} '
                                 f'AuthEntity from the one used in this ContextService.')

        quotas_update_values = update_values.pop('quotas', None)

        if quotas_update_values:
            context_quotas_service = ContextQuotasService(context)
            context_quotas_service.update_context_quotas(update_values=quotas_update_values)
        return context

    def assign_user(self, user: AuthEntity, context: Context = None, name: str = None) -> Context:
        if not context:
            context = self.get_context(name=name)
        else:
            if context.owner != self.application_service:
                raise ValueError(f'Referenced context is owned by a different {AuthEntityType.APPLICATION_SERVICE} '
                                 f'AuthEntity from the one used in this ContextService.')

        participation_service = ParticipationService(context)
        participation_service.add_to_context(user)
        return context

    def remove_user(self, user: AuthEntity, context: Context = None, name: str = None) -> Context:
        if not context:
            context = self.get_context(name=name)
        else:
            if context.owner != self.application_service:
                raise ValueError(f'Referenced context is owned by a different {AuthEntityType.APPLICATION_SERVICE} '
                                 f'AuthEntity from the one used in this ContextService.')

        participation_service = ParticipationService(context)
        participation_service.remove_from_context(user)
        return context


class ContextQuotasService(BaseService):

    def __init__(self, context: Context):
        self.context = context

    def create_context_quotas(self, **optional) -> ContextQuotas:
        context_quotas = ContextQuotas(context=self.context, **optional)
        context_quotas.full_clean()
        context_quotas.save()
        return context_quotas

    def update_context_quotas(self, *, update_values: dict) -> ContextQuotas:
        context_quotas = self.context.quotas

        context_quotas = ContextQuotasService._update_instance(context_quotas, **update_values)
        context_quotas.full_clean()
        context_quotas.save()

        return context_quotas