import re
from argparse import ArgumentParser
from shutil import copymode, move
from tempfile import mkstemp

from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import get_random_secret_key

import os


def apply_secret_key(file_path, secret_key):
    # Snippet by Thomas Watnedal (https://stackoverflow.com/a/39110)

    fh, abs_path = mkstemp()
    secret_key_applied = False
    with os.fdopen(fh, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                if not secret_key_applied:
                    match = re.match('^(SECRET_KEY\s*=\s*).*$', line)
                    if match is not None:
                        secret_key_declaration = match.group(1)
                        line = f'{secret_key_declaration}\'{secret_key}\'\n'
                        secret_key_applied = True
                new_file.write(line)

    # Copy the file permissions from the old file to the new file
    copymode(file_path, abs_path)

    # Move new file
    move(abs_path, file_path)


class Command(BaseCommand):
    help = 'Auxiliary script for generating new Django secret keys for deployment purposes'

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument('-f', '--settings-file', help='Path to a settings file. If given, the secret key will not '
                                                          'echoed in stdout, but the value will be put in settings '
                                                          'file, directly, instead.')

    def handle(self, *args, **options):
        secret_key = get_random_secret_key()
        if options['settings_file'] is not None:
            expanded_file_path = os.path.expanduser(os.path.expandvars(options['settings_file']))
            if os.path.exists(expanded_file_path) and os.path.isfile(expanded_file_path):
                # Settings file exist
                apply_secret_key(expanded_file_path, secret_key)
                print(f'Secret key applied in settings file at "{expanded_file_path}"!')
            else:
                print(f'ERROR: Settings file "{expanded_file_path}" either does not exist or is not a file')
        else:
            print(secret_key)
