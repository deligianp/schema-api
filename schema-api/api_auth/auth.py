from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from django.utils.translation import gettext_lazy as _

from api_auth.models import ApiToken
from api_auth.services import ApiTokenService


class ApiTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        prefix = settings.AUTHORIZATION_HEADER_PREFIX

        if not header:
            return None
        if header[0].decode('utf-8') != prefix:
            # Authorization header is possibly for another backend
            return None
        if len(header) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(header) > 2:
            msg = _('Invalid token header. '
                    'Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        token = header[1].decode('utf-8')
        try:
            authenticated = ApiTokenService.authenticate(token)
        except (ApiToken.DoesNotExist, ValueError):
            raise exceptions.AuthenticationFailed('Invalid token')

        if authenticated[1] is not None:
            user = authenticated[1].user
            request.context = authenticated[1].context
        else:
            user = authenticated[0]

        return user, token
