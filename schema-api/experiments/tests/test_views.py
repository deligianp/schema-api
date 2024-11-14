from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Participation, Context, Task
from api.serializers import TasksBasicListSerializer
from api_auth.models import ApiToken
from api_auth.services import ApiTokenService
from experiments.models import Experiment
from experiments.serializers import ExperimentSerializer, ExperimentsListSerializer
from util.defaults import get_current_datetime


class ExperimentsAPIViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        user = UserModel.objects.create(username='user')
        context = Context.objects.create(owner=user, name='context')
        other_context = Context.objects.create(owner=user, name='othercontext')
        participation = Participation.objects.create(user=user, context=context)
        other_participation = Participation.objects.create(user=user, context=other_context)
        cls.api_key = '0123456789abcdef'
        ApiToken.objects.create(
            participation=participation,
            key=cls.api_key[:settings.TOKEN_KEY_LENGTH],
            digest=ApiTokenService._hash_token(cls.api_key),
            expiry=get_current_datetime() + timedelta(days=1)
        )

        cls.experiments = [
            Experiment.objects.create(name='experiment0', creator=user, context=context),
            Experiment.objects.create(name='experiment1', creator=user, context=context),
            Experiment.objects.create(name='experiment2', creator=user, context=context)
        ]

        cls.other_api_key = '0123456789abcdf0'
        ApiToken.objects.create(
            participation=other_participation,
            key=cls.other_api_key[:settings.TOKEN_KEY_LENGTH],
            digest=ApiTokenService._hash_token(cls.other_api_key),
            expiry=get_current_datetime() + timedelta(days=1)
        )

        cls.valid_input_data = {
            'name': 'experiment',
            'description': 'Experiment description'
        }

    def test_create_experiment_endpoint_returns_201_and_experiment_data_when_name_is_given(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data.pop('description')
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_subset = {
            'name': 'experiment',
            'description': ''
        }
        self.assertEqual(response.data, response.data | expected_subset)
        self.assertIn('creator', response.data)
        self.assertIn('created_at', response.data)

    def test_create_experiment_endpoint_returns_201_and_experiment_data_when_name_and_description_is_given(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_subset = {
            'name': 'experiment',
            'description': 'Experiment description'
        }
        self.assertEqual(response.data, response.data | expected_subset)
        self.assertIn('creator', response.data)
        self.assertIn('created_at', response.data)

    def test_create_experiment_endpoint_returns_400_when_name_is_not_given(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data.pop('name')
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_endpoint_returns_400_when_name_is_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data['name'] = ''
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_endpoint_returns_400_when_name_is_null(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data['name'] = None
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_endpoint_returns_400_when_name_is_whitespace(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data['name'] = ' '
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_endpoint_returns_400_when_name_is_not_slug(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data['name'] = 'New experiment'
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_endpoint_returns_400_when_description_is_null(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data['description'] = None
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experiment_endpoint_returns_409_when_name_is_not_available_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        input_data = self.valid_input_data.copy()
        input_data['name'] = 'experiment0'
        response = self.client.post(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_list_experiments_endpoint_returns_200_and_empty_experiments_list_when_no_experiments_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.other_api_key)
        url = reverse('experiments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(response.data, [])

    def test_list_experiments_endpoint_returns_200_and_experiments_list(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(response.data, ExperimentsListSerializer(self.experiments, many=True).data)


class ExperimentDetailsAPIViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        user = UserModel.objects.create(username='user')
        context = Context.objects.create(owner=user, name='context')
        other_context = Context.objects.create(owner=user, name='othercontext')
        participation = Participation.objects.create(user=user, context=context)
        other_participation = Participation.objects.create(user=user, context=other_context)
        cls.api_key = '0123456789abcdef'
        ApiToken.objects.create(
            participation=participation,
            key=cls.api_key[:settings.TOKEN_KEY_LENGTH],
            digest=ApiTokenService._hash_token(cls.api_key),
            expiry=get_current_datetime() + timedelta(days=1)
        )


        Experiment.objects.create(name='experiment0', creator=user, context=context)
        cls.ref_experiment = Experiment.objects.create(name='experiment1', creator=user, context=context)

        cls.valid_input_data = {
            'name': 'experiment',
            'description': 'Experiment description'
        }

    def test_update_experiment_endpoint_returns_202_and_experiment_data_when_name_updated(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data.pop('description')
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data, ExperimentSerializer(self.ref_experiment).data | input_data)

    def test_update_experiment_endpoint_returns_202_and_experiment_data_when_description_updated(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data.pop('name')
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data, ExperimentSerializer(self.ref_experiment).data | input_data)

    def test_update_experiment_endpoint_returns_202_and_experiment_data_when_both_name_and_description_updated(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data, ExperimentSerializer(self.ref_experiment).data | input_data)

    def test_update_experiment_endpoint_returns_404_when_experiment_does_not_exist_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, 'unknown_experiment'])
        input_data = self.valid_input_data.copy()
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_experiment_endpoint_returns_404_when_referenced_user_does_not_participate_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=['unknown_username', 'unknown_experiment'])
        input_data = self.valid_input_data.copy()
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_experiment_endpoint_returns_400_when_updated_name_is_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data['name'] = ''
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_experiment_endpoint_returns_400_when_updated_name_is_null(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data['name'] = None
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_experiment_endpoint_returns_400_when_updated_name_is_whitespace(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data['name'] = ' '
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_experiment_endpoint_returns_400_when_updated_name_is_not_slug(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data['name'] = 'New experiment'
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_experiment_endpoint_returns_409_when_updated_name_is_not_available_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data['name'] = 'experiment0'
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_experiment_endpoint_returns_400_when_updated_description_is_null(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data['description'] = None
        response = self.client.patch(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_experiment_endpoint_returns_200_and_experiment_data(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, ExperimentSerializer(self.ref_experiment).data)

    def test_retrieve_experiment_endpoint_returns_404_when_experiment_does_not_exist_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, 'unknown_experiment'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_experiment_endpoint_returns_404_when_referenced_user_does_not_participate_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=['unknown_username', 'unknown_experiment'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_experiment_endpoint_returns_204(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_experiment_endpoint_returns_404_when_experiment_does_not_exist(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=[self.ref_experiment.creator.username, 'unknown_experiment'])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_experiment_endpoint_returns_404_when_referenced_user_does_not_participate_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-details', args=['unknown_user', 'unknown_experiment'])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ExperimentTasksAPIViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        user = UserModel.objects.create(username='user')
        context = Context.objects.create(owner=user, name='context')
        participation = Participation.objects.create(user=user, context=context)
        cls.api_key = '0123456789abcdef'
        ApiToken.objects.create(
            participation=participation,
            key=cls.api_key[:settings.TOKEN_KEY_LENGTH],
            digest=ApiTokenService._hash_token(cls.api_key),
            expiry=get_current_datetime() + timedelta(days=1)
        )

        cls.ref_experiment = Experiment.objects.create(name='experiment0', creator=user, context=context)

        cls.old_tasks = [
            Task.objects.create(user=user, context=context, name='task2'),
            Task.objects.create(user=user, context=context, name='task3')
        ]
        cls.ref_experiment.tasks.set(cls.old_tasks)

        cls.tasks = [
            Task.objects.create(user=user, context=context, name='task2'),
            Task.objects.create(user=user, context=context, name='task3')
        ]

        cls.other_experiment = Experiment.objects.create(name='experiment1', creator=user, context=context)

        cls.valid_input_data = [
            str(t.uuid) for t in cls.tasks
        ]

    def test_set_experiment_tasks_returns_202_and_basic_list_of_tasks(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        response = self.client.put(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data, TasksBasicListSerializer(self.tasks, many=True).data)

    def test_set_experiment_tasks_returns_404_when_experiment_does_not_exist_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.ref_experiment.creator.username, 'unknown_experiment'])
        input_data = self.valid_input_data.copy()
        response = self.client.put(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_experiment_tasks_returns_404_when_referenced_user_does_not_participate_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=['unknown_username', 'unknown_experiment'])
        input_data = self.valid_input_data.copy()
        response = self.client.put(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_experiment_tasks_returns_404_when_any_of_the_referenced_tasks_not_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        input_data = self.valid_input_data.copy()
        input_data.append('ef41158d-3100-4809-92db-703945ce4aa1')
        response = self.client.put(url, data=input_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_experiment_tasks_returns_400_when_no_tasks_are_given(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_experiment_tasks_returns_200_and_experiment_tasks_data(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.ref_experiment.creator.username, self.ref_experiment.name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, TasksBasicListSerializer(self.old_tasks, many=True).data)

    def test_list_experiment_tasks_returns_200_and_empty_experiment_tasks_list_when_no_tasks_in_experiment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.other_experiment.creator.username, self.other_experiment.name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_experiment_tasks_returns_404_when_experiment_does_not_exist_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=[self.other_experiment.creator.username, 'unknown_experiment'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_experiment_tasks_returns_404_when_user_does_not_participate_in_context(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key)
        url = reverse('experiment-tasks', args=['unknown_username', 'unknown_experiment'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
