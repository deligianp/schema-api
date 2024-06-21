from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination


class ApplicationPagination(LimitOffsetPagination):
    max_limit = settings.MAX_PAGINATION_LIMIT
    default_limit = settings.DEFAULT_PAGINATION_LIMIT

    def __init__(self, *args, **kwargs):
        super(ApplicationPagination,self).__init__(*args, **kwargs)