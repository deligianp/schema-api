# Models:
# - ApiAuthToken
#       - Must extend from knox's auth token (meaning it should have a field for token hash, part of token, expiration
#         date and refernce to user. Thus test that model has fields token token_key, digest, user, created, expiry and
#         the additional fields of 'can_gererate_api_keys'.
#       - Restrict ApiAuthToken model to either have 'can_generate_tokens' True and no related projects
#       - Or have 'can_generate_tokens' to false with one related project
#       - Restrict that ApiAuthToken can have at maximum one related project (one token per project)
#       - Restrict that the length of the part of token stored is 4
#
# - Project
#       - Need to have a name
#       - Need to have a related ApiAuthToken
#       -
from django.db.models import OneToOneField
from django.test import TestCase

from api_auth.models import ApiAuthToken


class ApiAuthTokenTestCase(TestCase):

    def test_api_auth_token_extends_knox_auth_token(self):
        expected_one_to_one_field = 'authtoken_ptr'
        [related_field] = [_ for _ in ApiAuthToken._meta.concrete_fields if _.name == expected_one_to_one_field]
        self.assertIs(related_field.__class__, OneToOneField)
        self.assertEqual(related_field.related_model.__name__, 'AuthToken')
        self.assertEqual(related_field.related_model.__module__, 'knox.models')

    def test_concrete_fields(self):
        expected_fields = {'token_key', 'digest', 'created', 'user', 'expiry', 'can_generate_tokens', 'authtoken_ptr'}
        self.assertSetEqual(set(f.name for f in ApiAuthToken._meta.concrete_fields), expected_fields)

