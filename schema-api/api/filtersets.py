from django.db.models import Q
from django_filters import rest_framework as filters

from api.constants import _TaskStatus


class TaskFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = filters.MultipleChoiceFilter(choices=_TaskStatus.choices)
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
