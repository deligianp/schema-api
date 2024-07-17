from django.test import TestCase
from django.urls import reverse, resolve

from api_auth.views import ContextsAPIView, ContextDetailsAPIView


class ApiUrlsCase(TestCase):

    def test_reverse_user_contexts_is_expected_url(self):
        expected = '/api/contexts'
        self.assertEquals(reverse('user-contexts'),expected)

    def test_reverse_user_context_details_is_expected_url(self):
        expected = '/api/contexts/name'
        self.assertEquals(reverse('user-context-details', args=['name']), expected)

    def test_user_contexts_url_routes_to_expected_api_view(self):
        resolved = resolve('/api/contexts')
        self.assertEquals(resolved.func.view_class, ContextsAPIView)

    def test_user_context_details_url_routes_to_expected_api_view(self):
        resolved = resolve('/api/contexts/name')
        self.assertEquals(resolved.func.view_class, ContextDetailsAPIView)
