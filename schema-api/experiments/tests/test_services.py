from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.models import Context, Participation, Task
from experiments.models import Experiment
from experiments.services import ExperimentService, ExperimentTaskService
from util.exceptions import ApplicationDuplicateError, ApplicationValidationError, ApplicationNotFoundError, \
    ApplicationImplicitPermissionError


class ExperimentServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.creator = UserModel(username='creator')
        cls.creator.save()
        cls.other_creator = UserModel(username='othercreator')
        cls.other_creator.save()
        cls.context = Context(owner=cls.creator, name='context')
        cls.context.save()
        cls.other_context = Context(owner=cls.other_creator, name='othercontext')
        cls.other_context.save()

        participation = Participation(user=cls.creator, context=cls.context)
        participation.save()

        cls.experiment0 = Experiment(creator=cls.creator, context=cls.context, name='experiment0')
        cls.experiment0.save()
        cls.experiment1 = Experiment(creator=cls.creator, context=cls.context, name='experiment1')
        cls.experiment1.save()
        cls.experiment2 = Experiment(creator=cls.other_creator, context=cls.context, name='experiment2')
        cls.experiment2.save()
        cls.context_experiments = [cls.experiment0, cls.experiment1, cls.experiment2]
        cls.creator_experiments = [cls.experiment0, cls.experiment1]

    def test_instantiate_service_creates_experiment_service_with_given_context(self):
        experiment_service = ExperimentService(context=self.context)
        self.assertEqual(experiment_service.context, self.context)

    def test_create_experiment_creates_experiment_with_given_name_and_creator(self):
        experiment_service = ExperimentService(context=self.context)
        experiment_name = 'experiment'
        mocked_datetime = datetime(
            2020, 1, 1, 1, 1, 1, tzinfo=timezone.utc
        )
        with patch('django.utils.timezone.now', return_value=mocked_datetime):
            experiment = experiment_service.create_experiment(name=experiment_name, creator=self.creator)
        self.assertEqual(experiment.name, experiment_name)
        self.assertEqual(experiment.creator, self.creator)
        self.assertEqual(experiment.context, self.context)
        self.assertEqual(experiment.description, '')
        self.assertEqual(experiment.created_at, mocked_datetime)

    def test_create_experiment_raises_application_duplicate_error_when_experiment_name_is_not_unique_for_creator_and_context(
            self):
        experiment_service = ExperimentService(context=self.context)
        experiment_service.create_experiment(name='experiment', creator=self.creator)
        with self.assertRaises(ApplicationDuplicateError):
            experiment_service.create_experiment(name='experiment', creator=self.creator)

    def test_create_experiment_raises_application_validation_error_on_invalid_experiment_data(self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationValidationError) as ave:
            experiment = experiment_service.create_experiment(name='', creator=None, description=None, created_at=None)

    def test_list_experiments_returns_experiments_related_to_context(self):
        experiment_service = ExperimentService(context=self.context)
        experiments = experiment_service.list_experiments()
        self.assertListEqual(list(experiments), self.context_experiments)

    def test_list_experiments_returns_no_experiments_no_experiments_exist_in_context(self):
        experiment_service = ExperimentService(context=self.other_context)
        experiments = experiment_service.list_experiments()
        self.assertListEqual(list(experiments), [])

    def test_list_experiments_by_creator_returns_experiments_created_by_user_in_corresponding_context(self):
        experiment_service = ExperimentService(context=self.context)
        experiments = experiment_service.list_experiments_by_creator(self.creator)
        self.assertListEqual(list(experiments), self.creator_experiments)

    def test_list_experiments_by_creator_returns_no_experiments_if_user_has_no_experiments_in_corresponding_context(
            self):
        experiment_service = ExperimentService(context=self.other_context)
        experiments = experiment_service.list_experiments_by_creator(self.creator)
        self.assertListEqual(list(experiments), [])

    def test_retrieve_experiment_returns_experiment_by_name_and_given_creator(self):
        experiment_service = ExperimentService(context=self.context)
        experiment = experiment_service.retrieve_experiment(self.creator_experiments[0].name, self.creator)
        self.assertEqual(experiment.name, self.creator_experiments[0].name)

    def test_retrieve_experiment_raises_application_not_found_error_when_no_experiment_exists_with_given_name_for_creator(
            self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationNotFoundError):
            experiment = experiment_service.retrieve_experiment('unknown_experiment', self.creator)

    def test_update_experiment_updates_experiment_only_by_name_and_description(self):
        experiment_service = ExperimentService(context=self.context)
        updated_data = {
            'name': 'experiment_update',
            'description': 'description_update',
            'created_at': datetime(2021, 2, 2, 2, 2, 2, tzinfo=timezone.utc),
            'creator': self.other_creator,
            'context': self.other_context
        }
        experiment = experiment_service.update_experiment(self.creator, 'experiment0', **updated_data)
        self.assertEqual(experiment.name, updated_data['name'])
        self.assertEqual(experiment.description, updated_data['description'])
        self.assertNotEqual(experiment.created_at, updated_data['created_at'])
        self.assertEqual(experiment.created_at, self.experiment0.created_at)
        self.assertNotEqual(experiment.creator, updated_data['creator'])
        self.assertEqual(experiment.creator, self.experiment0.creator)
        self.assertNotEqual(experiment.context, updated_data['context'])
        self.assertEqual(experiment.context, self.experiment0.context)

    def test_update_experiment_raises_application_duplicate_error_when_experiment_name_is_not_unique_for_creator(self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationDuplicateError):
            experiment_service.update_experiment(self.creator, 'experiment0', name='experiment1')

    def test_update_experiment_raises_application_validation_error_when_name_is_not_slug(self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationValidationError):
            experiment_service.update_experiment(self.creator, 'experiment0', name='experiment 0')

    def test_update_experiment_raises_application_validation_error_when_name_is_none(self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationValidationError):
            experiment_service.update_experiment(self.creator, 'experiment0', name=None)

    def test_update_experiment_raises_application_validation_error_when_name_is_empty(self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationValidationError):
            experiment_service.update_experiment(self.creator, 'experiment0', name='')

    def test_update_experiment_raises_application_validation_error_when_description_is_none(self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationValidationError):
            experiment_service.update_experiment(
                self.creator, 'experiment0', name='new_experiment', description=None
            )

    def test_update_experiment_raises_application_not_found_error_when_no_experiment_exists_with_given_name_for_creator(
            self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationNotFoundError):
            experiment_service.update_experiment(self.creator, 'experiment9', name='experiment')

    def test_delete_experiment_deletes_experiment_by_name_and_creator(self):
        experiment_service = ExperimentService(context=self.context)
        experiment_service.delete_experiment(name='experiment0', creator=self.creator)
        with self.assertRaises(Experiment.DoesNotExist):
            Experiment.objects.get(name='experiment0', creator=self.creator, context=self.context)

    def test_delete_experiment_raises_application_not_found_error_when_no_experiment_exists_with_given_name_for_creator(
            self):
        experiment_service = ExperimentService(context=self.context)
        with self.assertRaises(ApplicationNotFoundError):
            experiment_service.delete_experiment(name='experiment9', creator=self.creator)


class ExperimentTaskServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.creator = UserModel.objects.create(username='creator')
        cls.context = Context.objects.create(owner=cls.creator, name='context')
        cls.other_context = Context.objects.create(owner=cls.creator, name='other_context')
        cls.experiment = Experiment.objects.create(name='experiment', context=cls.context, creator=cls.creator)
        cls.tasks = [
            Task.objects.create(user=cls.creator, context=cls.context, name='task0'),
            Task.objects.create(user=cls.creator, context=cls.context, name='task1'),
            Task.objects.create(user=cls.creator, context=cls.context, name='task2')
        ]

        cls.experiment.tasks.set(cls.tasks)

    def test_set_tasks_changes_related_tasks(self):
        experiment_task_service = ExperimentTaskService(self.experiment)
        new_tasks = [
            Task.objects.create(name='task3', context=self.context, user=self.creator),
            Task.objects.create(name='task4', context=self.context, user=self.creator)
        ]
        experiment_task_service.set_tasks(new_tasks)

        self.assertListEqual(list(self.experiment.tasks.all()), new_tasks)

    def test_set_tasks_with_empty_list_unsets_tasks(self):
        experiment_task_service = ExperimentTaskService(self.experiment)
        new_tasks = []
        experiment_task_service.set_tasks(new_tasks)

        self.assertListEqual(list(self.experiment.tasks.all()), new_tasks)

    def test_set_tasks_raises_application_implicit_permission_error_when_task_not_in_corresponding_context(self):
        experiment_task_service = ExperimentTaskService(self.experiment)
        new_tasks = [
            Task.objects.create(name='task3', context=self.context, user=self.creator),
            Task.objects.create(name='task4', context=self.other_context, user=self.creator)
        ]
        with self.assertRaises(ApplicationImplicitPermissionError):
            experiment_task_service.set_tasks(new_tasks)

    def test_get_tasks_returns_experiment_tasks(self):
        experiment_task_service = ExperimentTaskService(self.experiment)
        self.assertListEqual(list(experiment_task_service.get_tasks()), self.tasks)
