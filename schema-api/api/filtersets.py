from django_filters import rest_framework as filters

from api.constants import TaskStatus


class TaskFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = filters.MultipleChoiceFilter(choices=TaskStatus.choices)
    after = filters.DateTimeFilter(field_name='submitted_at', lookup_expr='gte')
    before = filters.DateTimeFilter(field_name='submitted_at', lookup_expr='lt')

