from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from api.models import Context
from experiments.models import Experiment
from util.defaults import get_current_datetime


class ExperimentTestCase(TestCase):
    fields = {f.name for f in Experiment._meta.fields if f.concrete}

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

    def test_save(self):
        experiment_data = {
            'name': 'experiment',
            'description': 'description',
            'created_at': get_current_datetime(),
            'creator': self.creator,
            'context': self.context
        }
        experiment = Experiment(**experiment_data)
        experiment.save()
        experiment.refresh_from_db()
        self.assertEqual(experiment.name, experiment_data['name'])
        self.assertEqual(experiment.description, experiment_data['description'])
        self.assertEqual(experiment.created_at, experiment_data['created_at'])
        self.assertEqual(experiment.creator, experiment_data['creator'])
        self.assertEqual(experiment.context, experiment_data['context'])

    def test_name_default_empty_string(self):
        experiment = Experiment()
        self.assertEqual(experiment.name, '')

    def test_name_cannot_be_none(self):
        experiment = Experiment(name=None)
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'name'}), validate_constraints=False, validate_unique=False
            )

    def test_name_cannot_be_blank(self):
        experiment = Experiment(name='')
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'name'}), validate_constraints=False, validate_unique=False
            )

    def test_name_is_slug(self):
        experiment = Experiment(name='Not a slug')
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'name'}), validate_constraints=False, validate_unique=False
            )

    def test_name_is_unique_for_creator_and_context(self):
        experiment = Experiment(name='experiment0', creator=self.creator, context=self.context)
        experiment.save()

        experiment = Experiment(name='experiment0', creator=self.other_creator, context=self.context)
        experiment.full_clean(exclude=self.fields.difference({'name', 'creator', 'context'}))

        experiment = Experiment(name='experiment0', creator=self.other_creator, context=self.other_context)
        experiment.full_clean(exclude=self.fields.difference({'name', 'creator', 'context'}))

        experiment = Experiment(name='experiment0', creator=self.creator, context=self.other_context)
        experiment.full_clean(exclude=self.fields.difference({'name', 'creator', 'context'}))

        experiment = Experiment(name='experiment0', creator=self.creator, context=self.context)
        with self.assertRaises(ValidationError):
            experiment.full_clean(exclude=self.fields.difference({'name', 'creator', 'context'}))

    def test_description_cannot_be_none(self):
        experiment = Experiment(description=None)
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'description'}), validate_constraints=False, validate_unique=False
            )

    def test_description_default_empty_string(self):
        experiment = Experiment()
        self.assertEqual(experiment.description, '')

    def test_created_at_cannot_be_none(self):
        experiment = Experiment(created_at=None)
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'created_at'}), validate_constraints=False, validate_unique=False
            )

    def test_created_at_default_current_timestamp(self):
        mocked_datetime = datetime(
            2020, 1, 1, 1, 1, 1, tzinfo=timezone.utc
        )
        with patch('django.utils.timezone.now', return_value=mocked_datetime):
            experiment = Experiment()
            self.assertEqual(experiment.created_at, mocked_datetime)

    def test_creator_cannot_be_none(self):
        experiment = Experiment(creator=None)
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'creator'}), validate_constraints=False, validate_unique=False
            )

    def test_context_cannot_be_none(self):
        experiment = Experiment(context=None)
        with self.assertRaises(ValidationError):
            experiment.full_clean(
                exclude=self.fields.difference({'context'}), validate_constraints=False, validate_unique=False
            )
