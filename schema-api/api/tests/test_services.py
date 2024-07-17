from django.test import TestCase

from api.models import Context, Participation
from api.services import UserContextService
from api_auth.constants import AuthEntityType
from api_auth.models import AuthEntity
from util.exceptions import ApplicationError, ApplicationNotFoundError


class UserContextTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        app_service = AuthEntity.objects.create(username='as', entity_type=AuthEntityType.APPLICATION_SERVICE)
        cls.contexts = {
            'context0': Context.objects.create(owner=app_service, name='context0'),
            'context1': Context.objects.create(owner=app_service, name='context1'),
            'context2': Context.objects.create(owner=app_service, name='context2')
        }
        cls.user0 = AuthEntity.objects.create(username='user0', parent=app_service)
        Participation.objects.create(user=cls.user0, context=cls.contexts['context0'])
        Participation.objects.create(user=cls.user0, context=cls.contexts['context1'])
        cls.user1 = AuthEntity.objects.create(username='user1', parent=app_service)

    def test_list_contexts_returns_only_users_contexts(self):
        ucs = UserContextService(self.user0)
        contexts = ucs.list_contexts()
        expected = [self.contexts['context0'], self.contexts['context1']]
        self.assertEqual(len([c for c in contexts]), len(expected))
        for c in contexts:
            self.assertIn(c, expected)

    def test_list_contexts_returns_no_contexts_if_user_not_in_any_context(self):
        ucs = UserContextService(self.user1)
        contexts = ucs.list_contexts()
        self.assertEqual(len([c for c in contexts]), 0)

    def test_get_context_returns_context_referenced_by_provided_name(self):
        ucs = UserContextService(self.user0)
        context = ucs.retrieve_context('context1')
        self.assertEqual(context, self.contexts['context1'])

    def test_get_context_raises_application_not_found_error_on_no_match(self):
        ucs = UserContextService(self.user0)
        with self.assertRaises(ApplicationNotFoundError):
            ucs.retrieve_context(3)
