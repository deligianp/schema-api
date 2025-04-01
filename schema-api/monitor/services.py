from typing import Dict

from django.conf import settings
from django.core.cache import cache
from django.db.models import OuterRef, Subquery, Count, Avg, ExpressionWrapper, F, DurationField, Sum

from api.constants import TaskStatus
from api.models import Task, StatusHistoryPoint
from api_auth.constants import AuthEntityType


class ApplicationServiceMonitoringService:

    def __init__(self, application_service: settings.AUTH_USER_MODEL):
        if application_service.entity_type != AuthEntityType.APPLICATION_SERVICE:
            raise ValueError(f'Service must use an auth entity of type {AuthEntityType.APPLICATION_SERVICE}')
        self.application_service = application_service

    def _extract_metrics(self) -> Dict[str, object]:
        latest_status_log_by_task = (
            StatusHistoryPoint.objects
            .filter(task=OuterRef('pk'))
            .order_by('-created_at')[:1]
        )

        tasks = (
            Task.objects
            .annotate(status=Subquery(latest_status_log_by_task.values('status')))
            .annotate(latest_status_update=Subquery(latest_status_log_by_task.values('created_at')))
            .annotate(
                duration_since_last_update=ExpressionWrapper(
                    F('latest_status_update') - F('submitted_at'),
                    output_field=DurationField()
                )
            )
            .values(
                'status'
            )
            .annotate(num_executions=Count('id'))
            .annotate(accumulated_cpu_cores_claim=Sum('resources__cpu_cores'))
            .annotate(accumulated_ram_gb_claim=Sum('resources__ram_gb'))
            .annotate(accumulated_disk_gb_claim=Sum('resources__disk_gb'))
            .annotate(accumulated_duration_since_latest_update=Sum('duration_since_last_update'))
        )

        metrics = {
            'num_of_executions': sum(status_class['num_executions'] for status_class in tasks),
            'num_of_pending_executions': sum(status_class['num_executions'] for status_class in tasks if
                                             status_class['status'] in (
                                                 TaskStatus.SUBMITTED, TaskStatus.APPROVED, TaskStatus.SCHEDULED)),
            'num_of_running_executions': sum(status_class['num_executions'] for status_class in tasks if
                                             status_class['status'] in (TaskStatus.INITIALIZING, TaskStatus.RUNNING)),
            'num_of_completed_executions': sum(status_class['num_executions'] for status_class in tasks if
                                               status_class['status'] in (
                                                   TaskStatus.COMPLETED,)),
            'num_of_failed_executions': sum(status_class['num_executions'] for status_class in tasks if
                                            status_class['status'] in (
                                                TaskStatus.ERROR,)),
            'num_of_canceled_executions': sum(status_class['num_executions'] for status_class in tasks if
                                              status_class['status'] in (
                                                  TaskStatus.CANCELED,)),
            'active_cpu_cores': sum(status_class['accumulated_cpu_cores_claim'] for status_class in tasks if
                                    status_class['status'] in (
                                        TaskStatus.SUBMITTED, TaskStatus.APPROVED, TaskStatus.SCHEDULED,
                                        TaskStatus.INITIALIZING, TaskStatus.RUNNING)),
            'active_ram_gb': sum(status_class['accumulated_ram_gb_claim'] for status_class in tasks if
                                 status_class['status'] in (
                                     TaskStatus.SUBMITTED, TaskStatus.APPROVED, TaskStatus.SCHEDULED,
                                     TaskStatus.INITIALIZING, TaskStatus.RUNNING)),
            'active_disk_gb': sum(status_class['accumulated_disk_gb_claim'] for status_class in tasks if
                                  status_class['status'] in (
                                      TaskStatus.SUBMITTED, TaskStatus.APPROVED, TaskStatus.SCHEDULED,
                                      TaskStatus.INITIALIZING, TaskStatus.RUNNING)),
        }
        metrics['average_cpu_cores_claim'] = sum(
            status_class['accumulated_cpu_cores_claim'] for status_class in tasks) / metrics['num_of_executions']
        metrics['average_ram_gb_claim'] = sum(
            status_class['accumulated_ram_gb_claim'] for status_class in tasks) / metrics['num_of_executions']
        metrics['average_disk_gb_claim'] = sum(
            status_class['accumulated_disk_gb_claim'] for status_class in tasks) / metrics['num_of_executions']
        return metrics

    def get_metrics(self) -> Dict[str, object]:
        cache_key = 'monitoring:metrics'
        metrics = cache.get(cache_key)

        if not metrics:
            metrics = self._extract_metrics()
            cache.set(cache_key, metrics, timeout=settings.CACHE_TIMEOUT)

        return metrics
