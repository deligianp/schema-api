from django.urls import path

from experiments.views import ExperimentTasksAPIView, ExperimentDetailsAPIView, ExperimentsAPIView

urlpatterns = [
    path(r'experiments', ExperimentsAPIView.as_view(), name='experiments'),
    path(r'experiments/<username>/<name>', ExperimentDetailsAPIView.as_view(), name='experiment-details'),
    path(r'experiments/<username>/<name>/tasks', ExperimentTasksAPIView.as_view(), name='experiment-tasks'),
]
