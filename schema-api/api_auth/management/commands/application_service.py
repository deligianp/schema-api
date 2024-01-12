import json
import re
from argparse import ArgumentParser

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils.text import slugify

from api_auth.serializers import UserDetailsSerializer
from api_auth.services import AuthEntityService, ApiTokenService
from util.commands import ApplicationBaseCommand
from util.exceptions import ApplicationError


class Command(ApplicationBaseCommand):
    # TODO: Consider the implementation of management commands as a client that uses API endpoints with administrative
    #       permissions
    help = 'Manage application services'

    def add_arguments(self, parser: ArgumentParser):
        subparsers = parser.add_subparsers(help='sub-command help', dest='command0')

        register_context_manager_parser = subparsers.add_parser('register', help='Register a new application service')
        register_context_manager_parser.add_argument('name', help='Unique name of application service')

        list_context_manager_parser = subparsers.add_parser('list', help='List application services')

        retrieve_context_manager_parser = subparsers.add_parser('get',
                                                                help='Retrieve details of an application service')
        retrieve_context_manager_parser.add_argument('name', help='Unique name of application service')

        ref_application_service_parser = subparsers.add_parser('for',
                                                               help='Perform an action for a specific application'
                                                                    ' service')
        ref_application_service_parser.add_argument('name', help='Unique name of referenced application service')

        ref_subparsers = ref_application_service_parser.add_subparsers(help='actions', dest='command1')

        ref_api_key_parser = ref_subparsers.add_parser('apikeys', aliases=['keys'])
        ref_api_key_parser_set = ref_api_key_parser.add_subparsers(help='subcontext', dest='command2')
        ref_issue_api_key_parser = ref_api_key_parser_set.add_parser('issue')
        ref_issue_api_key_parser.add_argument('-d', '--duration', help='TTL descriptor for the issued token',
                                              default='1h'
                                              )
        ref_list_api_keys_parser = ref_api_key_parser_set.add_parser('list')
        ref_list_api_keys_parser.add_argument('-a', '--all', action='store_true')
        ref_list_api_keys_parser.add_argument('-e', '--expired', action='store_true')

        ref_get_api_key_parser = ref_api_key_parser_set.add_parser('get')
        ref_get_api_key_parser.add_argument('uuid_prefix', help='Prefix of UUID identifier for specific API key(s)')

        ref_revoke_api_key_parser = ref_api_key_parser_set.add_parser('revoke')
        ref_revoke_api_key_parser.add_argument('uuid_prefix', help='Prefix of UUID identifier for specific API key(s)')

    def handle(self, *args, **options):
        application_service_name = options.get('name')
        if options['command0'] == 'register':
            try:
                application_service = AuthEntityService.create_application_service(application_service_name)
            except Exception as ex:
                if options['verbosity'] > 0:
                    self.log_application_error(ex, context_fields=['username', settings.NON_FIELD_ERRORS_KEY])
                exit(1)
            if options['verbosity'] > 0:
                return self.style.SUCCESS(f'\u2713 New application service named "{application_service_name}" '
                                          f'successfully registered')
        elif options['command0'] == 'list':
            application_services = AuthEntityService.get_application_services()
            if options['verbosity'] > 0 and len(application_services) > 0:
                self.stdout.write('\n'.join(f'{_as.username}' for _as in application_services))
        elif options['command0'] == 'get' or options['command0'] == 'for':
            try:
                application_service = AuthEntityService.get_application_service(application_service_name)
            except ApplicationError as ex:
                self.log_application_error(ex, context_fields=['username', settings.NON_FIELD_ERRORS_KEY])
                exit(1)
            if options['command0'] == 'for':
                if options['command1'] == 'apikeys':
                    self.handle_apikeys(*args, **options, application_service=application_service)
                    return
            output_serializer = UserDetailsSerializer(application_service)
            self.stdout.write(json.dumps(output_serializer.data))

    def handle_apikeys(self, *args, application_service, **options):
        # TODO: Consider whether moving API key management to a different command is desirable
        if options['command2'] == 'issue':
            duration_descriptor = options['duration']

            api_token_service = ApiTokenService(application_service)
            token, token_obj = api_token_service.issue_token(duration=duration_descriptor)
            self.stdout.write(self.style.SUCCESS(
                f'\u2713 New token was issued for application service named {application_service.username}'
            ))
            token_out = f'{" TOKEN START ":#^72}\n{token}\n{" TOKEN END ":#^72}'
            self.stdout.write(self.style.ERROR(token_out))
        elif options['command2'] == 'list':
            # TODO: Implement list retrieval of API keys
            pass
        elif options['command2'] == 'get':
            # TODO: Implement details retrieval of API keys
            pass
        elif options['command2'] == 'revoke':
            # TODO: Implement revocation of API keys
            pass
