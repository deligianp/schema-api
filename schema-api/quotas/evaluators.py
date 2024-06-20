from abc import ABC, abstractmethod

from api.models import Task, ResourceSet
from quotas.exceptions import QuotaSoftViolationError, QuotaHardViolationError
from quotas.models import Quotas


class QuotasEvaluator(ABC):

    @staticmethod
    @abstractmethod
    def evaluate(context_quotas: Quotas, participation_quotas: Quotas, task: Task):
        pass


class ActiveResourcesDbQuotasEvaluator(QuotasEvaluator):

    @staticmethod
    def evaluate(context_quotas: Quotas, participation_quotas: Quotas, task: Task):
        resources: ResourceSet = task.resources

        context_stats = ResourceSet.objects.filter(task__pending=True, task__context=task.context).exclude(
            task__id=task.id
        ).values(
            'cpu_cores', 'ram_gb', 'disk_gb', 'task__user'
        )
        ActiveResourcesDbQuotasEvaluator._evaluate_for_all(context_quotas, resources, *context_stats, is_context_evaluation=True)

        participation_stats = [s for s in context_stats if s['task__user'] == task.user.id]
        ActiveResourcesDbQuotasEvaluator._evaluate_for_all(participation_quotas, resources, *participation_stats)

    @staticmethod
    def _evaluate_for_all(quotas: Quotas, requested: ResourceSet, *current: dict, is_context_evaluation=False):
        aggregates = {
            'cpu_cores': 0,
            'ram_gb': 0,
            'disk_gb': 0
        }
        if quotas.max_active_tasks and len(current) + 1 > quotas.max_active_tasks:
            raise QuotaSoftViolationError(
                'max_active_tasks',
                is_context_evaluation,
                current=len(current),
                requested=1,
                limit=quotas.max_active_tasks,
            )
        for row in current:
            aggregates['cpu_cores'] += row['cpu_cores'] if row['cpu_cores'] is not None else 0
            aggregates['ram_gb'] += row['ram_gb'] if row['ram_gb'] is not None else 0
            aggregates['disk_gb'] += row['disk_gb'] if row['disk_gb'] is not None else 0

        if quotas.max_active_cpu_cores is not None and aggregates['cpu_cores'] + requested.cpu_cores > quotas.max_active_cpu_cores:
            raise QuotaSoftViolationError(
                'max_active_cpu_cores',
                is_context_evaluation,
                current=aggregates['cpu_cores'],
                requested=requested.cpu_cores,
                limit=quotas.max_active_cpu_cores,
            )
        if quotas.max_active_ram_gb is not None and aggregates['ram_gb'] + requested.ram_gb > quotas.max_active_ram_gb:
            raise QuotaSoftViolationError(
                'max_active_ram_gb',
                is_context_evaluation,
                current=aggregates['ram_gb'],
                requested=requested.ram_gb,
                limit=quotas.max_active_ram_gb,
            )
        if quotas.max_active_disk_gb is not None and aggregates['disk_gb'] + requested.disk_gb > quotas.max_active_disk_gb:
            raise QuotaSoftViolationError(
                'max_active_disk_gb',
                is_context_evaluation,
                current=aggregates['disk_gb'],
                requested=requested.disk_gb,
                limit=quotas.max_active_disk_gb,
            )


class RequestedResourcesQuotasEvaluator(QuotasEvaluator):

    @staticmethod
    def evaluate(context_quotas: Quotas, participation_quotas: Quotas, task: Task):
        task_resources: ResourceSet = task.resources
        executors = task.executors
        if context_quotas.max_cpu_cores_request and context_quotas.max_cpu_cores_request < task_resources.cpu_cores:
            raise QuotaSoftViolationError(
                'max_cpu_cores_request',
                True,
                requested=task_resources.cpu_cores,
                limit=context_quotas.max_cpu_cores_request,
            )
        if context_quotas.max_ram_gb_request and context_quotas.max_ram_gb_request < task_resources.ram_gb:
            raise QuotaSoftViolationError(
                'max_ram_gb_request',
                True,
                requested=task_resources.ram_gb,
                limit=context_quotas.max_ram_gb_request,
            )
        if context_quotas.max_disk_gb_request and context_quotas.max_disk_gb_request < task_resources.disk_gb:
            raise QuotaSoftViolationError(
                'max_disk_gb_request',
                True,
                requested=task_resources.disk_gb,
                limit=context_quotas.max_disk_gb_request,
            )
        if context_quotas.max_executors_request and context_quotas.max_executors_request < len(executors.all()):
            raise QuotaSoftViolationError(
                'max_executors_request',
                True,
                requested=len(executors.all()),
                limit=context_quotas.max_executors_request,
            )

        if participation_quotas.max_cpu_cores_request and participation_quotas.max_cpu_cores_request < task_resources.cpu_cores:
            raise QuotaSoftViolationError(
                'max_cpu_cores_request',
                False,
                requested=task_resources.cpu_cores,
                limit=participation_quotas.max_cpu_cores_request,
            )
        if participation_quotas.max_ram_gb_request and participation_quotas.max_ram_gb_request < task_resources.ram_gb:
            raise QuotaSoftViolationError(
                'max_ram_gb_request',
                False,
                requested=task_resources.ram_gb,
                limit=participation_quotas.max_ram_gb_request,
            )
        if participation_quotas.max_disk_gb_request and participation_quotas.max_disk_gb_request < task_resources.disk_gb:
            raise QuotaSoftViolationError(
                'max_disk_gb_request',
                False,
                requested=task_resources.disk_gb,
                limit=participation_quotas.max_disk_gb_request,
            )
        if participation_quotas.max_executors_request and participation_quotas.max_executors_request < len(executors.all()):
            raise QuotaSoftViolationError(
                'max_executors_request',
                False,
                requested=len(executors.all()),
                limit=participation_quotas.max_executors_request,
            )


class TasksQuotasEvaluator(QuotasEvaluator):

    @staticmethod
    def evaluate(context_quotas: Quotas, participation_quotas: Quotas, task: Task):
        context_stats = Task.objects.filter(pending=True, context=task.context).exclude(
            id=task.id
        )

        if context_quotas.total_tasks and context_quotas.total_tasks < context_stats.count()+1:
            raise QuotaHardViolationError(
                'total_tasks',
                True,
                current=context_stats.count(),
                requested=1,
                limit=context_quotas.total_tasks,
            )
        participation_stats = context_stats.filter(user=task.user)
        if participation_quotas.total_tasks and participation_quotas.total_tasks < participation_stats.count()+1:
            raise QuotaHardViolationError(
                'total_tasks',
                False,
                current=participation_stats.count(),
                requested=1,
                limit=participation_quotas.total_tasks,
            )
