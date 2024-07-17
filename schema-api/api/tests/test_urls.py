from django.test import TestCase
from django.urls import reverse, resolve

from api.views import UserContextInfoAPIView
from api_auth.views import ContextsAPIView, ContextDetailsAPIView


class ApiUrlsCase(TestCase):

    def test_reverse_user_contexts_is_expected_url(self):
        expected = '/api/contexts'
        self.assertEqual(reverse('user-contexts'),expected)

    def test_reverse_user_context_details_is_expected_url(self):
        expected = '/api/contexts/name'
        self.assertEqual(reverse('user-context-details', args=['name']), expected)

    # Test for temporary endpoint url - expected to be removed in the future
    def test_reverse_user_context_info_is_expected_url(self):
        expected = '/api/context-info'
        self.assertEqual(reverse('user-context-info'), expected)

    def test_user_contexts_url_routes_to_expected_api_view(self):
        resolved = resolve('/api/contexts')
        self.assertEqual(resolved.func.view_class, ContextsAPIView)

    def test_user_context_details_url_routes_to_expected_api_view(self):
        resolved = resolve('/api/contexts/name')
        self.assertEqual(resolved.func.view_class, ContextDetailsAPIView)

    # Test for temporary endpoint url routing - expected to be removed in the future
    def test_user_context_info_url_routes_to_expected_api_view(self):
        resolved = resolve('/api/context-info')
        self.assertEqual(resolved.func.view_class, UserContextInfoAPIView)