from datetime import datetime, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from api.models import Context, Participation
from api_auth.constants import AuthEntityType
from api_auth.models import AuthEntity, ApiToken
from api_auth.services import ApiTokenService


class UserContextsAPITestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        app_service = AuthEntity.objects.create(username='as', entity_type=AuthEntityType.APPLICATION_SERVICE)
        cls.contexts = {
            'context0': Context.objects.create(owner=app_service, name='context0'),
            'context1': Context.objects.create(owner=app_service, name='context1'),
            'context2': Context.objects.create(owner=app_service, name='context2')
        }
        cls.user0 = AuthEntity.objects.create(username='user0', parent=app_service)
        cls.user1 = AuthEntity.objects.create(username='user1', parent=app_service)
        cls.user2 = AuthEntity.objects.create(username='user2', parent=app_service, is_active=False)

        Participation.objects.create(user=cls.user0, context=cls.contexts['context0'])
        Participation.objects.create(user=cls.user0, context=cls.contexts['context1'])
        Participation.objects.create(user=cls.user1, context=cls.contexts['context2'])
        p = Participation.objects.create(user=cls.user1, context=cls.contexts['context0'])
        Participation.objects.create(user=cls.user2, context=cls.contexts['context0'])

        ats = ApiTokenService(cls.user0, cls.contexts['context0'])
        cls.u0c0_key, _ = ats.issue_token(duration='1d', title='valid')
        cls.u0c0_key_expired, key = ats.issue_token(duration='1d', title='expired',
                                                    created=timezone.now() - timedelta(days=2),
                                                    expiry=timezone.now() - timedelta(days=1))
        cls.u0c0_key_inactive, _ = ats.issue_token(duration='1d', is_active=False, title='inactive')
        ats = ApiTokenService(cls.user1, cls.contexts['context0'])
        cls.u1c0_key, _ = ats.issue_token(duration='1d')
        ats = ApiTokenService(cls.user2, cls.contexts['context0'])
        cls.u2c0_key, _ = ats.issue_token(duration='1d')
        ats = ApiTokenService(app_service)
        cls.svc_key, _ = ats.issue_token(duration='1d')

        p.delete()

    # Test API permissions
    def test_poll_api_with_no_credentials_is_forbidden(self):
        self.client.credentials()
        url = reverse('user-contexts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_inactive_api_key_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key_inactive)
        url = reverse('user-contexts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_expired_api_key_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key_expired)
        url = reverse('user-contexts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_inactive_user_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u2c0_key)
        url = reverse('user-contexts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_stale_credentials_of_deleted_participation_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u1c0_key)
        url = reverse('user-contexts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_contexts_for_user_returns_user_related_contexts(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key)
        url = reverse('user-contexts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn(
            {'name': 'context0'}, response.data
        )
        self.assertIn(
            {'name': 'context1'}, response.data
        )

    # Inapplicable for now, in order to have an API key to call the API, a user must have issued one base on a context
    # that he participates at the time of the request
    # def test_list_contexts_for_user_returns_empty_list_when_user_has_no_context(self):
    #     pass


class UserContextDetailsAPITestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        app_service = AuthEntity.objects.create(username='as', entity_type=AuthEntityType.APPLICATION_SERVICE)
        cls.contexts = {
            'context0': Context.objects.create(owner=app_service, name='context0'),
            'context1': Context.objects.create(owner=app_service, name='context1'),
            'context2': Context.objects.create(owner=app_service, name='context2')
        }
        cls.user0 = AuthEntity.objects.create(username='user0', parent=app_service)
        cls.user1 = AuthEntity.objects.create(username='user1', parent=app_service)
        cls.user2 = AuthEntity.objects.create(username='user2', parent=app_service, is_active=False)
        Participation.objects.create(user=cls.user0, context=cls.contexts['context0'])
        Participation.objects.create(user=cls.user0, context=cls.contexts['context1'])
        Participation.objects.create(user=cls.user1, context=cls.contexts['context2'])

        p = Participation.objects.create(user=cls.user1, context=cls.contexts['context0'])
        Participation.objects.create(user=cls.user2, context=cls.contexts['context0'])
        ats = ApiTokenService(cls.user0, cls.contexts['context0'])
        cls.u0c0_key, _ = ats.issue_token(duration='1d', title='valid')
        cls.u0c0_key_expired, key = ats.issue_token(duration='1d', title='expired',
                                                    created=timezone.now() - timedelta(days=2),
                                                    expiry=timezone.now() - timedelta(days=1))
        cls.u0c0_key_inactive, _ = ats.issue_token(duration='1d', is_active=False, title='inactive')
        ats = ApiTokenService(cls.user1, cls.contexts['context0'])
        cls.u1c0_key, _ = ats.issue_token(duration='1d')
        ats = ApiTokenService(cls.user2, cls.contexts['context0'])
        cls.u2c0_key, _ = ats.issue_token(duration='1d')
        ats = ApiTokenService(app_service)
        cls.svc_key, _ = ats.issue_token(duration='1d')

        p.delete()

    # Test API permissions
    def test_poll_api_with_no_credentials_is_forbidden(self):
        self.client.credentials()
        url = reverse('user-context-details', args=['name'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_inactive_api_key_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key_inactive)
        url = reverse('user-context-details', args=['name'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_expired_api_key_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key_expired)
        url = reverse('user-context-details', args=['name'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_inactive_user_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u2c0_key)
        url = reverse('user-context-details', args=['name'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poll_api_with_stale_credentials_of_deleted_participation_is_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u1c0_key)
        url = reverse('user-context-details', args=['name'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_context_returns_context_details(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key)
        url = reverse('user-context-details', args=['context0'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertEqual(
            [
                {
                    'username': 'user0',
                    'is_active': True
                },
                {
                    'username': 'user2',
                    'is_active': False
                }
            ],
            response.data['users']
        )
        self.assertIn('quotas', response.data)

    def test_retrieve_context_with_invalid_context_name_raises_404_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.u0c0_key)
        url = reverse('user-context-details', args=['context2'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
