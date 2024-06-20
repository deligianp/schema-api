import sys

from django.apps import AppConfig
from django.conf import settings


class ApiAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_auth'

    def ready(self):
        self._validate_settings()

    def _validate_settings(self):
        token_length = settings.TOKEN_BYTE_LENGTH

        supported_key_lengths = [64, 128, 256]
        if token_length not in supported_key_lengths:
            raise ValueError(
                f'Invalid token bit-length: {token_length}. '
                f'Choose from: {", ".join(str(_) for _ in supported_key_lengths)}')

        # token_ttl_descriptor = settings.TOKEN_TTL_DESCRIPTOR
        # if token_ttl_descriptor is not None:
        #     td = utils.parse_duration(token_ttl_descriptor)
        #     if td.years + td.months + td.weeks + td.days == 0:
        #         raise ValueError('Token TTL is defined so that tokens should expire instantly.')
        # else:
        #     print(
        #         'No token TTL was given, thus tokens will never expire.'
        #         ' This might be a security issue - consider using a sensible TTL according to the token bit size.'
        #     )
