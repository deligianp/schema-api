from rest_framework.exceptions import ValidationError


def namespace(*values):
    if values:
        tokens = list(values[:-1]) + [str(values[-1])]
        return '.'.join(tokens)
    return ''


def denamespace(namespaced_value):
    tokens = namespaced_value.split('.')
    return '.'.join(tokens[:-1]), tokens[-1]


def get_primary_validation_error_message(exception: ValidationError) -> str:
    field_errors = exception.get_full_details()
    field = list(field_errors.keys())[0]
    return f'Field [{field}]: {field_errors[field][0]["message"]}'
