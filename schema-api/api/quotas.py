import abc

from django.db.models import Q, Sum

from api.constants import _TaskStatus
from api.models import Task
from util.exceptions import ApplicationTaskQuotaDepletedError, ApplicationTaskQuotaExceedingRequestError


class AbstractQuotaPolicy:

    def check_quotas(self, task: Task):
        self._check_max_tasks(task)
        self._check_max_active_tasks(task)
        self._check_max_cpu_cores(task)
        self._check_max_ram_gb(task)

    @abc.abstractmethod
    def _check_max_cpu_cores(self, task: Task):
        pass

    @abc.abstractmethod
    def _check_max_tasks(self, task: Task):
        pass

    @abc.abstractmethod
    def _check_max_ram_gb(self, task: Task):
        pass

    @abc.abstractmethod
    def _check_max_active_tasks(self, task: Task):
        pass


class DefaultQuotaPolicy(AbstractQuotaPolicy):

    def _check_max_cpu_cores(self, task: Task):
        allocated_cpu = Task.objects.filter(
            ~Q(status__in=(_TaskStatus.SUBMITTED, _TaskStatus.REJECTED)), pending=True, context=task.context
        ).aggregate(Sum('resourceset__cpu_cores'))['resourceset__cpu_cores__sum'] or 0
        if allocated_cpu >= task.context.quotas.max_cpu:
            raise ApplicationTaskQuotaDepletedError('All CPU cores for this context are currently allocated')
        elif allocated_cpu + task.resourceset.cpu_cores > task.context.quotas.max_cpu:
            raise ApplicationTaskQuotaExceedingRequestError(
                f'{task.resourceset.cpu_cores} CPU cores were to be allocated but '
                f'only {task.context.quotas.max_cpu - allocated_cpu} are available in this context'
            )

    def _check_max_tasks(self, task: Task):
        context_tasks_qs = Task.objects.filter(context=task.context)
        n_completed_tasks = context_tasks_qs.filter(
            Q(Q(status=_TaskStatus.COMPLETED) | Q(status=_TaskStatus.ERROR))).count()
        if n_completed_tasks >= task.context.quotas.max_tasks:
            raise ApplicationTaskQuotaDepletedError('All tasks reserved for this context have already been ran')

        n_running_tasks = context_tasks_qs.filter(~Q(status__in=(_TaskStatus.REJECTED, _TaskStatus.SUBMITTED)),
                                                  pending=True).count()
        if n_completed_tasks + n_running_tasks >= task.context.quotas.max_tasks:
            raise ApplicationTaskQuotaDepletedError(
                'Currently running tasks have allocated the reserved number of tasks for this context')

    def _check_max_ram_gb(self, task: Task):
        allocated_ram_gb = Task.objects.filter(
            ~Q(status__in=(_TaskStatus.SUBMITTED, _TaskStatus.REJECTED)), pending=True, context=task.context
        ).aggregate(Sum('resourceset__ram_gb'))['resourceset__ram_gb__sum'] or 0
        if allocated_ram_gb >= task.context.quotas.max_ram_gb:
            raise ApplicationTaskQuotaDepletedError('All RAM for this context is currently allocated')
        elif allocated_ram_gb + task.resourceset.ram_gb > task.context.quotas.max_ram_gb:
            raise ApplicationTaskQuotaExceedingRequestError(
                f'{task.resourceset.ram_gb} GBs of RAM were to be allocated but '
                f'only {task.context.quotas.max_ram_gb - allocated_ram_gb} are available in this context'
            )

    def _check_max_active_tasks(self, task: Task):
        if Task.objects.filter(~Q(status__in=(_TaskStatus.SUBMITTED, _TaskStatus.REJECTED)),
                               pending=True, context=task.context).count() >= task.context.quotas.max_active_tasks:
            raise ApplicationTaskQuotaDepletedError(
                'Maximum number of active/concurrent tasks for this context is currently running')
