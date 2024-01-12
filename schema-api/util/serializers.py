from collections import OrderedDict

from rest_framework import serializers


class KVPairsField(serializers.DictField):
    def __init__(self, key_field_name: str = 'key', value_field_name: str = 'value', **kwargs):
        self.key_field_name = key_field_name
        self.value_field_name = value_field_name
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        return [{'key': key, 'value': value} for key, value in data.items()]

    def to_representation(self, value):
        kv_pairs = value.all()
        return {kvp.key: kvp.value for kvp in kv_pairs}


class ModelMemberRelatedField(serializers.ListField):
    def __init__(self, target_field_name=None, **kwargs):
        self.target_field_name = target_field_name
        super(ModelMemberRelatedField, self).__init__(**kwargs)

    def to_representation(self, data):
        related = data.all()
        extended_value = [getattr(_, self.target_field_name) for _ in related]
        whole_value = super(ModelMemberRelatedField, self).to_representation(extended_value)
        return whole_value


class OmitEmptyValuesMixin:

    def to_representation(self, value: serializers.Serializer):
        repr_dict = super(OmitEmptyValuesMixin, self).to_representation(value)
        return OrderedDict((k, v) for k, v in repr_dict.items()
                           if v not in [None, [], '', {}])