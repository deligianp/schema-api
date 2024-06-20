from typing import Iterable

from django.core.management import BaseCommand

from util.exceptions import ApplicationError, ApplicationValidationError


class ApplicationBaseCommand(BaseCommand):

    def log_application_error(self, error, context_fields: Iterable = None):
        if isinstance(error, ApplicationError):
            error_message = None
            if isinstance(error, ApplicationValidationError):
                if context_fields:
                    i_context_fields = iter(context_fields)
                    while not error_message:
                        try:
                            f = next(i_context_fields)
                        except StopIteration:
                            break
                        error_message = error.message_dict.get(f)[0]
                if not error_message:
                    error_field = next(iter(error.message_dict.keys()))
                    error_message = f'{error_field}: {error.message_dict[error_field][0]}'
            else:
                error_message = str(error)
            self.stderr.write(error_message)
        else:
            raise error
