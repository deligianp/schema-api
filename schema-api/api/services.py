import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Iterable, List, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db import transaction
from django.db.models import QuerySet, OuterRef, Subquery
from django.utils import timezone

from api import taskapis
from api.constants import TaskStatus
from api.models import Task, Executor, Env, MountPoint, Volume, ResourceSet, ExecutorOutputLog, Context, \
    Participation, StatusHistoryPoint, Tag
from api.serializers import TaskSerializer
from api.utils import get_task_manager
from api_auth.constants import AuthEntityType
from api_auth.models import AuthEntity
from core.managers.base import ExecutionManifest, ExecutionDetails, UserInfo
from core.utils import get_manager
from quotas.evaluators import ActiveResourcesDbQuotasEvaluator, RequestedResourcesQuotasEvaluator, TasksQuotasEvaluator
from quotas.models import ContextQuotas
from quotas.services import QuotasService
from util.exceptions import ApplicationError, ApplicationErrorHelper, ApplicationNotFoundError, \
    ApplicationValidationError


class UserContextService:

    def __init__(self, auth_entity: AuthEntity):
        self.auth_entity = auth_entity

    def list_contexts(self) -> Iterable[Context]:
        return self.auth_entity.contexts.all()

    def retrieve_context(self, name: str) -> Context:
        try:
            return self.auth_entity.contexts.get(name=name)
        except Context.DoesNotExist as dne:
            raise ApplicationNotFoundError from dne


class TaskService:

    def __init__(self, context=None, auth_entity=None):
        self.context = context
        self.auth_entity = auth_entity

    @transaction.atomic
    def submit_task(self, *, executors: Iterable[Executor], **optional):
        input_mount_points = optional.pop('inputs', None)
        output_mount_points = optional.pop('outputs', None)
        volumes = optional.pop('volumes', None)
        tags = optional.pop('tags', None)
        resource_set = optional.pop('resources', None)

        task = Task.objects.create(context=self.context, user=self.auth_entity, **optional)

        task_status_log_service = TaskStatusLogService(task)
        task_status_log_service.log_status_update(TaskStatus.SUBMITTED)

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
        else:
            ResourceSet.objects.create(task=task)

        if tags:
            tag_set = set(tags)
            for tag in tag_set:
                temp_tag = Tag.objects.get_or_create(value=tag)[0]
                task.tags.add(temp_tag)

        quotas_service = QuotasService(task.context, task.user)
        context_quotas, participation_quotas = quotas_service.get_qualified_quotas()
        RequestedResourcesQuotasEvaluator.evaluate(context_quotas, participation_quotas, task)
        TasksQuotasEvaluator.evaluate(context_quotas, participation_quotas, task)
        ActiveResourcesDbQuotasEvaluator.evaluate(context_quotas, participation_quotas, task)

        task_status_log_service.log_status_update(TaskStatus.APPROVED)

        task_serializer = TaskSerializer(task)
        task_data = task_serializer.data
        if manager_name := get_task_manager():
            manager = get_manager(manager_name)
            execution_details = ExecutionDetails(definition=json.dumps(task_data), is_task=True)
            user_info = UserInfo(unique_id=str(self.auth_entity.uuid), username=self.auth_entity.username,
                                 fs_user_dir=self.auth_entity.profile.fs_user_dir)
            execution_manifest = ExecutionManifest(
                execution=execution_details, user_info=user_info, context_id=str(self.context.id)
            )
            task.backend_ref = manager.submit(execution_manifest)
            task.manager_name = manager_name

            task.save()

            task_status_log_service.log_status_update(TaskStatus.QUEUED)
        return task

    def get_task(self, task_uuid: uuid.UUID):
        try:
            task = self.get_tasks().get(uuid=task_uuid)
        except Task.DoesNotExist as dne:
            raise ApplicationNotFoundError(f'No task was found with UUID "{task_uuid}"') from dne
        return task

    def get_task_stdout(self, task_uuid: uuid.UUID):
        task = self.get_task(task_uuid)

        executors_stdout = [
            executor_output_log.stdout for executor_output_log in ExecutorOutputLog.objects.filter(executor__task=task)
        ]
        return executors_stdout

    def get_task_stderr(self, task_uuid: uuid.UUID):
        task = self.get_task(task_uuid)

        executors_stderr = [
            executor_output_log.stderr for executor_output_log in ExecutorOutputLog.objects.filter(executor__task=task)
        ]
        return executors_stderr

    def get_tasks(self) -> QuerySet[Task]:
        return Task.objects.filter(context=self.context, user=self.auth_entity)

    def cancel_task(self, task_uuid: uuid.UUID) -> None:
        task = self.get_task(task_uuid)

        task_status_log_service = TaskStatusLogService(task)

        if not task_status_log_service.is_task_pending():
            return

        # If manager no longer exists in configuration, then raise an uncaught error
        # Probably will have to change it in the future
        manager = get_manager(task.manager_name)

        manager.cancel(task.backend_ref)
        task_status_log_service.log_status_update(TaskStatus.CANCELED, avoid_duplicates=True)

    @staticmethod
    @transaction.atomic
    def synchronize_dispatched_executions(tasks_qs: QuerySet[Task]):

        grouped = defaultdict(list)
        for t in tasks_qs:
            grouped[t.manager_name].append(t)

        for manager_name, manager_tasks in grouped.items():
            backend_refs = [w.backend_ref for w in manager_tasks]

            manager = get_manager(manager_name)
            live_data_map = dict(manager.list(ref_ids=backend_refs))

            for t in manager_tasks:
                task_live_data = live_data_map[t.backend_ref]

                task_status_log_service = TaskStatusLogService(t)
                task_status_log_service.update_live_data(task_live_data.status_history)


class StatusHistoryPointService:

    def __init__(self, task: Task):
        self.task = task

    def update_status(self, status: TaskStatus, update_time: datetime = None) -> StatusHistoryPoint:
        update_time = update_time or timezone.now()
        return StatusHistoryPoint.objects.create(task=self.task, status=status, created_at=update_time)

    def get_status_history(self) -> QuerySet[StatusHistoryPoint]:
        return StatusHistoryPoint.objects.filter(task=self.task).order_by('-update_time')

    def get_current_status(self) -> StatusHistoryPoint:
        return self.get_status_history().first()


class TaskStatusLogService:

    def __init__(self, task: Task):
        self.task = task

    @staticmethod
    def filter_tasks_by_status(queryset: QuerySet[Task], statuses: Iterable[TaskStatus]) -> QuerySet[
        Task]:

        latest_statuses = StatusHistoryPoint.objects.filter(
            task=OuterRef('pk')
        ).order_by('-status', '-created_at')

        tasks_with_latest_status = queryset.annotate(
            latest_status=Subquery(latest_statuses.values('status')[:1])
        )

        return tasks_with_latest_status.filter(latest_status__in=statuses)

    @transaction.atomic
    def update_live_data(self, live_status_history: List[Tuple[TaskStatus, datetime]]):
        for sl in live_status_history:
            self.log_status_update(sl[0], created_at=sl[1], avoid_duplicates=True)

    def log_status_update(self, status: TaskStatus, avoid_duplicates: bool = False, **optional) -> StatusHistoryPoint:
        if avoid_duplicates:
            try:
                status_history_point, created = StatusHistoryPoint.objects.get_or_create(
                    task=self.task, status=status, defaults={
                        **optional,
                        "task": self.task,
                        "status": status
                    }
                )
                return status_history_point
            except MultipleObjectsReturned:
                return StatusHistoryPoint.objects.filter(task=self.task, status=status).order_by(
                    '-created_at').first()
        else:
            return StatusHistoryPoint.objects.create(task=self.task, status=status, **optional)

    def get_current_status(self) -> StatusHistoryPoint:
        return StatusHistoryPoint.objects.filter(task=self.task).order_by('-status', '-created_at').first()

    def is_task_pending(self) -> bool:
        current_status = self.get_current_status()
        return TaskStatus.SUBMITTED <= current_status.status <= TaskStatus.RUNNING

    def is_task_dispatched(self) -> bool:
        current_status = self.get_current_status()
        return TaskStatus.QUEUED <= current_status.status <= TaskStatus.RUNNING

    def does_task_await_dispatch(self):
        current_status = self.get_current_status()
        return TaskStatus.SUBMITTED <= current_status.status < TaskStatus.QUEUED


class ParticipationService:

    def __init__(self, context: Context):
        self.context = context

    def add_to_context(self, user: AuthEntity) -> Participation:
        if user.entity_type != AuthEntityType.USER:
            raise ApplicationError(f'Only {AuthEntityType.USER} type AuthEntities can be added to a context')

        if user.parent != self.context.owner:
            raise ApplicationError(f'Referenced user\'s parent is different from the context\'s application service')

        participation = Participation(user=user, context=self.context)
        try:
            participation.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        participation.save()
        return participation

    def get_participations(self) -> QuerySet[Participation]:
        return Participation.objects.filter(context=self.context)

    def get_participation(self, auth_entity: AuthEntity) -> Participation:
        try:
            return self.get_participations().get(user=auth_entity)
        except Participation.DoesNotExist:
            raise ApplicationNotFoundError(
                f'No participation exists for user {auth_entity.username} in context {self.context.name}')

    def remove_from_context(self, user: AuthEntity):
        participation = self.get_participation(user)
        participation.delete()


class ContextService:

    def __init__(self, application_service: AuthEntity):
        if application_service.entity_type != AuthEntityType.APPLICATION_SERVICE:
            raise ApplicationError(
                f'{self.__class__.__name__} depends on an AuthEntity of type {AuthEntityType.APPLICATION_SERVICE}'
            )

        self.application_service = application_service

    @transaction.atomic
    def create_context(self, *, name: str):
        # slugify name?

        context = Context(owner=self.application_service, name=name)
        try:
            context.full_clean()
        except ValidationError as ve:
            raise ApplicationErrorHelper.to_application_error(ve)
        context.save()

        context_quotas = ContextQuotas(context=context)
        context_quotas.save()

        return context

    def get_contexts(self) -> QuerySet:
        return Context.objects.filter(owner=self.application_service)

    def get_context(self, *, name: str) -> Context:
        try:
            return self.get_contexts().get(name=name)
        except Context.DoesNotExist:
            raise ApplicationNotFoundError(f'No context exists with name {name}')

    @transaction.atomic
    def update_context(self, *, update_values: dict, context: Context = None, name: str = None) -> Context:
        if not context:
            context = self.get_context(name=name)
        else:
            if context.owner != self.application_service:
                raise ApplicationError(
                    f'Referenced context is owned by a different {AuthEntityType.APPLICATION_SERVICE} AuthEntity from '
                    f'the one used in this ContextService.'
                )

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
                raise ApplicationError(
                    f'Referenced context is owned by a different {AuthEntityType.APPLICATION_SERVICE} AuthEntity from '
                    f'the one used in this ContextService.'
                )

        participation_service = ParticipationService(context)
        participation_service.add_to_context(user)
        return context

    def remove_user(self, user: AuthEntity, context: Context = None, name: str = None) -> Context:
        if not context:
            context = self.get_context(name=name)
        else:
            if context.owner != self.application_service:
                raise ApplicationError(
                    f'Referenced context is owned by a different {AuthEntityType.APPLICATION_SERVICE} AuthEntity from '
                    f'the one used in this ContextService.'
                )

        participation_service = ParticipationService(context)
        participation_service.remove_from_context(user)
        return context
