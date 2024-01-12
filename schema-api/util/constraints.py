from django.core.exceptions import ValidationError
from django.db.models import CheckConstraint, UniqueConstraint


class ApplicationConstraintContextMixin:

    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'error_context'):
            self.error_context = kwargs.pop('error_context', None)
        if not hasattr(self, 'error_code'):
            default_code = 'constraint_violated'
            if self.error_context:
                self.error_code = self.error_context.get('code', default_code)
            else:
                self.error_code = default_code
        super(ApplicationConstraintContextMixin, self).__init__(*args, **kwargs)

    def validate(self, *args, **kwargs):
        try:
            super(ApplicationConstraintContextMixin, self).validate(*args, **kwargs)
        except ValidationError as ve:
            ve.code = self.error_code
            if self.error_context:
                ve.context = self.error_context
            raise ve

    def deconstruct(self):
        _, args, kwargs = super(ApplicationConstraintContextMixin, self).deconstruct()
        if hasattr(self, 'error_context'):
            kwargs['error_context'] = self.error_context
        return _, args, kwargs


class ApplicationCheckConstraint(ApplicationConstraintContextMixin, CheckConstraint):
    error_code = 'check_violated'


class ApplicationUniqueConstraint(ApplicationConstraintContextMixin, UniqueConstraint):
    error_code = 'unique_violated'

    def __init__(self, *args, **kwargs):
        super(ApplicationUniqueConstraint, self).__init__(*args, **kwargs)
