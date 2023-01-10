from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils.text import slugify
from knox.models import AuthToken

from api_auth.services import AuthService


class Command(BaseCommand):
    help = 'Manage context_name managers'
    user_ref_aliases = ['user', 'context_manager_profile', 'context_name-manager']

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(help='sub-command help', dest='command')

        register_context_manager_parser = subparsers.add_parser('register', help='Register a new context_name manager')
        register_context_manager_parser.add_argument('context_name', help='Unique context_name of context_name manager')

        list_context_manager_parser = subparsers.add_parser('list', help='List context_name managers')

        retrieve_context_manager_parser = subparsers.add_parser('get', help='Retrieve details of a context_name manager')

        retrieve_subparsers = retrieve_context_manager_parser.add_subparsers(dest='command2')

        user_subparser = retrieve_subparsers.add_parser(self.user_ref_aliases[0], aliases=self.user_ref_aliases[1:])
        user_subparser.add_argument('context_name', help='Unique context_name of existing context_name manager')

        token_subparser = retrieve_subparsers.add_parser('token')
        token_subparser.add_argument('context_name', help='Unique context_name of existing context_name manager')

    def handle(self, *args, **options):
        if options['command'] == 'register':
            username = options['context_name']
            transformed_username = slugify(username)
            if username != transformed_username:
                response = None
                while response is None:
                    print(f'The name of a context_name manager must contain only characters, numbers, "-" or "_".')
                    print(f'The provided context_name manager name "{username}" contains not acceptable characters.')
                    print(f'As a result the name may be transformed to "{transformed_username}".')
                    response_input = input('Is this OK (Y/n)? ')
                    if response_input == '' or response_input.lower() == 'y':
                        response = True
                    elif response_input.lower() == 'n':
                        return
            try:
                context_manager, token = AuthService.register_context_manager(username=transformed_username)
            except IntegrityError as ie:
                print(ie)
                print(f'A context_name manager with context_name name "{transformed_username}" already exists.')
                return
            print(f'A new context_name manager was registered with context_name name {transformed_username}.')
            print(f'Token for user {transformed_username}: {token}')
        elif options['command'] == 'list':
            context_managers = AuthService.get_context_managers()
            print(
                f'{len(context_managers)} context_name manager{"s were" if len(context_managers) != 1 else " was"} '
                f'found{":" if len(context_managers) > 0 else ""}')
            if len(context_managers)>0:
                print('\n'.join(f'- {ap.username}' for ap in context_managers))
        elif options['command'] == 'get':
            username = options['context_name']
            if options['command2'] in self.user_ref_aliases:
                try:
                    context_manager = AuthService.get_context_manager(username=username)
                except User.DoesNotExist:
                    print(f'There is no context_name manager with context_name name {username}.')
                    return
                print(f'User {str(context_manager)}{"" if context_manager.is_active else " [INACTIVE]"}:')
                print(f'- Mail: {context_manager.email}')
                print(f'- Date registered: {context_manager.date_joined}')
                print(f'- Has API token: {"Yes" if context_manager.auth_token_set.exists() else "No"}')
            else:
                try:
                    auth_token = AuthService.get_context_manager_token(username=username)
                except AuthToken.DoesNotExist:
                    print(f'There is no context_name manager with context_name {username}.')
                    return
                print(f'First {len(auth_token)} letters of API token for user "{username}" is: {auth_token}')
