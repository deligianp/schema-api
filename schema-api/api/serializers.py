from django.conf import settings
from django.core.validators import MinValueValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.constants import MountPointTypes
from api.validators import NotEqualsValidator
from util.serializers import OmitEmptyValuesMixin, KVPairsField, ModelMemberRelatedField


class StrictSerializationMixin(serializers.Serializer):

    def validate(self, attrs):
        # pass
        # unknown = set(self.initial_data) - set(self.fields)
        # if unknown:
        #     raise ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


class BaseSerializer(OmitEmptyValuesMixin, StrictSerializationMixin, serializers.Serializer):
    pass


class ExecutorSerializer(BaseSerializer):
    image = serializers.CharField()
    command = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    stdout = serializers.CharField(required=False)
    stderr = serializers.CharField(required=False)
    stdin = serializers.CharField(required=False)
    workdir = serializers.CharField(required=False)
    env = KVPairsField(required=False, child=serializers.CharField(allow_blank=True), allow_empty=False, source='envs')


class MountPointSerializer(BaseSerializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    url = serializers.CharField()
    path = serializers.CharField()
    type = serializers.ChoiceField(choices=MountPointTypes.choices, default=MountPointTypes.FILE)

    def to_internal_value(self, data):
        return super(MountPointSerializer, self).to_internal_value(data)


class OutputMountPointSerializer(MountPointSerializer):
    def __init__(self, *args, **kwargs):
        super(OutputMountPointSerializer, self).__init__(*args, **kwargs)

    pass


class InputMountPointSerializer(MountPointSerializer):
    def __init__(self, *args, **kwargs):
        super(InputMountPointSerializer, self).__init__(*args, **kwargs)

    url = serializers.CharField(required=False)
    content = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if 'url' not in data and 'content' not in data:
            if data['type'] == 'DIRECTORY':
                raise ValidationError('An input "url" is required when defining a directory mountpoint.')
            raise ValidationError(
                detail='Either an input "url" must be provided or the "content" must be explicitly defined.'
            )
        if 'content' in data and data['type'] == 'DIRECTORY':
            raise ValidationError(
                detail='Provided content cannot be used in a directory.'
            )
        return super(InputMountPointSerializer, self).validate(data)


class ResourcesSerializer(BaseSerializer):
    cpu_cores = serializers.IntegerField(required=False,
                                         validators=[MinValueValidator(1)])
    preemptible = serializers.BooleanField(required=False)
    ram_gb = serializers.FloatField(required=False,
                                    validators=[NotEqualsValidator(0),
                                                MinValueValidator(0)])
    disk_gb = serializers.FloatField(required=False,
                                     validators=[NotEqualsValidator(0),
                                                 MinValueValidator(0)])
    zones = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=False)

    def validate(self, data):
        if len(data) == 0:
            raise ValidationError('A "resources" definition must have at least one of the following fields: ' +
                                  (', '.join(f'"{f}"' for f in list(self.fields.fields.keys()))) + '.')
        return super(ResourcesSerializer, self).validate(data)


class TaskSerializer(BaseSerializer):
    context = serializers.CharField(source='context.name', read_only=True)
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    status = serializers.CharField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)
    executors = ExecutorSerializer(many=True, allow_empty=False)
    inputs = InputMountPointSerializer(many=True, required=False, allow_empty=False)
    outputs = OutputMountPointSerializer(many=True, required=False, allow_empty=False)
    resources = ResourcesSerializer(required=False)
    volumes = ModelMemberRelatedField(target_field_name='path', child=serializers.CharField(), allow_empty=False,
                                      required=False)
    tags = KVPairsField(required=False, child=serializers.CharField(allow_blank=True), allow_empty=False)


class TasksBasicListSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    status = serializers.CharField(read_only=True)


class TasksDetailedListSerializer(TasksBasicListSerializer):
    context = serializers.CharField(source="context.name", read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)


class TasksFullListSerializer(TasksDetailedListSerializer):
    description = serializers.CharField()


class TasksListQPSerializer(serializers.Serializer):
    view = serializers.ChoiceField(('basic', 'detailed', 'full'), required=False, default='basic')


