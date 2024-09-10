from django.db.models import Q, OuterRef, Subquery
from django_filters import rest_framework as filters

from api.constants import _TaskStatus
from api.models import StatusHistoryPoint


class TaskFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = filters.MultipleChoiceFilter(choices=[(c.label, c.value) for c in _TaskStatus], method='filter_by_status')
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
        target_statuses = [_TaskStatus[v.upper()].value for v in value]

        latest_statuses = StatusHistoryPoint.objects.filter(
            task=OuterRef('pk')
        ).order_by('-created_at')

        tasks_with_latest_status = queryset.annotate(
            latest_status=Subquery(latest_statuses.values('status')[:1])
        )

        return tasks_with_latest_status.filter(latest_status__in=target_statuses)
