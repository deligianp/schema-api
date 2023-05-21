from typing import Iterable


def not_updatable(cls):
    save_method = cls.save

    def save(self, *args, **kwargs):
        if self.pk is not None:
            return
        save_method(self, *args, **kwargs)

    cls.save = save
    return cls


def update_fields(*_update_fields: Iterable[str], raise_exception: bool = False):
    """Update fields Django model decorator

    Args:
        _update_fields (Iterable[str]): A list of the field names of the Django model class that should be allowed to
            be updated. An empty field will be interpreted as no fields should be updated.
        raise_exception (bool, optional): Controls whether an exception should be raised when a restricted field is
            attempted to be updated. Defaults to False.

            This should be used with caution, since in order to perform this check an additional transaction is
            performed, which could be inefficient. If it's False, developers that use the model in their code should
            always keep in mind that after an update, on a model that this decorator is applied, not every field's
            value is guaranteed to have been persisted in the database - only allowed fields will pass their values to
            the corresponding database columns

    """
    update_fields_set = set(_update_fields)

    def inner(cls):
        save_method = cls.save

        def save(self, *args, **kwargs):
            defined_update_fields = kwargs.get('update_fields', None)
            if kwargs.get('force_update', None) or defined_update_fields or self.id is not None:
                restricted_update_fields_set = set(defined_update_fields).intersection(
                    update_fields_set) if defined_update_fields is not None else update_fields_set

                if raise_exception:
                    # this should run only if raise_exception is True since it introduces an additional transaction for
                    # every update
                    persisted = cls.objects.get(id=self.id)
                    violating_field = next(
                        (f for f in persisted._meta.concrete_fields
                         if (
                                 getattr(persisted, f.name) != getattr(self, f.name) and
                                 f.name not in restricted_update_fields_set)
                         ), None
                    )
                    if violating_field:
                        raise AttributeError(
                            f'Field \'{violating_field}\' is to be updated but is not in the qualified '
                            f'update_fields list: {", ".join(restricted_update_fields_set)}'
                        )

                kwargs['update_fields'] = list(restricted_update_fields_set)

            save_method(self, *args, **kwargs)

        cls.save = save
        return cls

    return inner
