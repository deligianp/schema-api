from django.db.models.fields.related import RelatedField


class BaseService:

    @classmethod
    def _update_instance(cls, instance, **update_values):
        instance_fields = {field.name: field for field in instance._meta.concrete_fields}
        for update_field_name, update_field_value in update_values.items():
            field = instance_fields.get(update_field_name, None)
            if field is None:
                raise TypeError(f'"{update_field_name}" is not a valid update field')
            if isinstance(field, RelatedField):
                continue

            setattr(instance, update_field_name, update_field_value)
        return instance
