from django.db.models import Q
from django_filters import rest_framework as filters

from api.constants import TaskStatus
from api.services import TaskStatusLogService


class TaskFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = filters.MultipleChoiceFilter(choices=[(c.label, c.value) for c in TaskStatus], method='filter_by_status')
    after = filters.DateTimeFilter(field_name='submitted_at', lookup_expr='gte')
    before = filters.DateTimeFilter(field_name='submitted_at', lookup_expr='lt')
    order = filters.OrderingFilter(
        fields=(
            ('uuid', 'uuid'),
            ('status', 'status'),
            ('submitted_at', 'submitted_at')
        )
    )
    search = filters.CharFilter(method='filter_by_search')

    def filter_by_search(self, queryset, name, value):
        return queryset.filter(
            Q(uuid__icontains=value) | Q(name__icontains=value)
        )

    def filter_by_status(self, queryset, name, value):

        target_statuses = [TaskStatus[v] for v in value]
        return TaskStatusLogService.filter_tasks_by_status(queryset, target_statuses)
