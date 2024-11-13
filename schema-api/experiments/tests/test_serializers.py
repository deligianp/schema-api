import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import serializers

from api.models import Task, Context
from api_auth.services import AuthEntityService
from experiments.models import Experiment
from experiments.serializers import ExperimentsListSerializer, ExperimentSerializer

# We want to test that the serialized datetime is actually the one we expect based on a static datetime in the tests
#
# Since DRF chose to not follow the provided isoformat() method provided by datetime objects, the only way to test this
# now is to pass the static datetime, through the `to_representation()` method provided by DRF's DateTimeField, and
# assert that we get the same on the other end, when serializing the business model. Yeah...
datetime_field = serializers.DateTimeField()


class ExperimentListSerializerTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.user = UserModel.objects.create(username='user')
        cls.other_user = UserModel.objects.create(username='other_user')
        context = Context.objects.create(name='context', owner=cls.user)

        cls.static_created_at = datetime(year=2020, month=1, day=2, hour=3, minute=4, second=5)

        cls.experiments = [
            Experiment.objects.create(name='experiment0', created_at=cls.static_created_at, creator=cls.user, context=context),
            Experiment.objects.create(name='experiment1', created_at=cls.static_created_at, creator=cls.user, context=context),
            Experiment.objects.create(name='experiment2', created_at=cls.static_created_at, creator=cls.other_user, context=context),
        ]

    def test_list_serialize_experiment_returns_list_of_experiments(self):
        experiment_list_serializer = ExperimentsListSerializer(self.experiments, many=True)
        serialized = experiment_list_serializer.data
        self.assertEqual(len(serialized), 3)
        self.assertIn(
            {
                'name': 'experiment0',
                'creator': self.user.username,
                'created_at': datetime_field.to_representation(self.static_created_at)
            },
            serialized
        )
        self.assertIn(
            {
                'name': 'experiment2',
                'creator': self.other_user.username,
                'created_at': datetime_field.to_representation(self.static_created_at)
            },
            serialized
        )
        self.assertIn(
            {
                'name': 'experiment1',
                'creator': self.user.username,
                'created_at': datetime_field.to_representation(self.static_created_at)
            },
            serialized
        )


class ExperimentSerializerTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.user = UserModel.objects.create(username='user')
        cls.context = Context.objects.create(name='context', owner=cls.user)

        cls.static_created_at = datetime(year=2020, month=1, day=2, hour=3, minute=4, second=5)

        cls.exp0 = Experiment.objects.create(name='experiment0', description='experiment0_description',
                                             created_at=cls.static_created_at, creator=cls.user,
                                             context=cls.context)

    def test_serialize_experiment(self):
        expected = {
            'name': self.exp0.name,
            'created_at': datetime_field.to_representation(self.static_created_at),
            'description': self.exp0.description,
            'creator': self.exp0.creator.username
        }
        serialized = ExperimentSerializer(self.exp0).data
        self.assertDictEqual(expected, serialized)

    def test_deserialize_minimal_experiment_data(self):
        serialized = {
            'name': 'input_experiment',
        }
        expected = {
            'name': 'input_experiment'
        }
        serializer = ExperimentSerializer(data=serialized)
        serializer.is_valid(raise_exception=True)
        self.assertDictEqual(expected, serializer.validated_data)

    def test_deserialize_experiment_data_with_optional_values_provided(self):
        serialized = {
            'name': 'input_experiment',
            'description': 'input_experiment_description'
        }
        expected = {
            'name': 'input_experiment',
            'description': 'input_experiment_description'
        }
        serializer = ExperimentSerializer(data=serialized)
        serializer.is_valid(raise_exception=True)
        self.assertDictEqual(expected, serializer.validated_data)

    def test_deserialize_experiment_data_ignores_read_only_fields_if_given(self):
        serialized = {
            'name': 'input_experiment',
            'created_at': '2020-01-01T00:00:00+00:00',
            'creator': 'user'
        }
        expected = {
            'name': 'input_experiment'
        }
        serializer = ExperimentSerializer(data=serialized)
        serializer.is_valid(raise_exception=True)
        self.assertDictEqual(expected, serializer.validated_data)

    def test_deserialize_experiment_data_raises_error_when_name_not_provided(self):
        serialized = {
            'description': 'Input experiment description'
        }
        serializer = ExperimentSerializer(data=serialized)
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_deserialize_experiment_data_raises_error_when_name_is_none(self):
        serialized = {
            'name': None,
            'description': 'Input experiment description'
        }
        serializer = ExperimentSerializer(data=serialized)
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_deserialize_experiment_data_raises_error_when_name_is_empty(self):
        serialized = {
            'name': '',
            'description': 'Input experiment description'
        }
        serializer = ExperimentSerializer(data=serialized)
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_deserialize_experiment_data_raises_error_when_name_is_whitespace(self):
        serialized = {
            'name': '              ',
            'description': 'Input experiment description'
        }
        serializer = ExperimentSerializer(data=serialized)
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_deserialize_experiment_data_raises_error_when_name_is_not_slug(self):
        serialized = {
            'name': 'Input experiment',
            'description': 'Input experiment description'
        }
        serializer = ExperimentSerializer(data=serialized)
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_deserialize_experiment_data_raises_error_when_description_is_none(self):
        serialized = {
            'name': 'input_experiment',
            'description': None
        }
        serializer = ExperimentSerializer(data=serialized)
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)
