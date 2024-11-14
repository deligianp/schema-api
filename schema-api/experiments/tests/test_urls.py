from django.test import TestCase
from django.urls import reverse, resolve

from experiments.views import ExperimentsAPIView, ExperimentDetailsAPIView, ExperimentTasksAPIView


class ExperimentsUrlsTestCase(TestCase):

    def test_reverse_experiments_is_expected_url(self):
        expected_url = '/reproducibility/experiments'
        self.assertEqual(reverse('experiments'), expected_url)

    def test_experiment_url_routes_to_expected_api_view(self):
        resolved = resolve('/reproducibility/experiments')
        self.assertEqual(resolved.func.view_class, ExperimentsAPIView)

    def test_reverse_experiment_details_is_expected_url(self):
        expected_url = '/reproducibility/experiments/creator0/exp0'
        self.assertEqual(reverse('experiment-details', args=['creator0', 'exp0']), expected_url)

    def test_experiment_details_url_routes_to_expected_api_view(self):
        resolved = resolve('/reproducibility/experiments/creator0/exp0')
        self.assertEqual(resolved.func.view_class, ExperimentDetailsAPIView)

    def test_reverse_experiment_tasks_is_expected_url(self):
        expected_url = '/reproducibility/experiments/creator0/exp0/tasks'
        self.assertEqual(reverse('experiment-tasks', args=['creator0','exp0']), expected_url)

    def test_experiment_tasks_url_routes_to_expected_api_view(self):
        resolved = resolve('/reproducibility/experiments/creator0/exp0/tasks')
        self.assertEqual(resolved.func.view_class, ExperimentTasksAPIView)
