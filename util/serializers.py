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


class WritableStringRelatedField(serializers.StringRelatedField):

    def to_internal_value(self, data):
        return data


class OmitEmptyValuesMixin:

    def to_representation(self, value: serializers.Serializer):
        repr_dict = super(OmitEmptyValuesMixin, self).to_representation(value)
        return OrderedDict((k, v) for k, v in repr_dict.items()
                           if v not in [None, [], '', {}])