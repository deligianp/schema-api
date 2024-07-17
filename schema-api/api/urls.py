from django.urls import path

from api.views import UserQuotasAPIView, TasksListCreateAPIView, TaskRetrieveAPIView, TaskStdoutAPIView, \
    TaskStderrAPIView
from api_auth.views import ContextsAPIView, ContextDetailsAPIView

urlpatterns = [
    path(r'tasks', TasksListCreateAPIView.as_view(), name='tasks'),
    path(r'tasks/<uuid:uuid>', TaskRetrieveAPIView.as_view(), name='tasks2'),
    path(r'tasks/<uuid:uuid>/stdout', TaskStdoutAPIView.as_view(), name='task_stdout'),
    path(r'tasks/<uuid:uuid>/stderr', TaskStderrAPIView.as_view(), name='task_stderr'),
    path(r'contexts', ContextsAPIView.as_view(), name='user-contexts'),
    path(r'contexts/<name>', ContextDetailsAPIView.as_view(), name='user-context-details'),
    path(r'quotas', UserQuotasAPIView.as_view(), name='user_quotas'),
]
