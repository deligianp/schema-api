from collections import OrderedDict

from rest_framework import serializers

from api.models import Task, Executor, Env, MountPoint, Volume, Tag
from schema_api import settings
from util.serializers import KVPairsField, WritableStringRelatedField, OmitEmptyValuesMixin


class ExecutorSerializer(OmitEmptyValuesMixin, serializers.Serializer):
    command = serializers.ListField(child=serializers.CharField())
    image = serializers.CharField()
    stderr = serializers.CharField(required=False)
    stdin = serializers.CharField(required=False)
    stdout = serializers.CharField(required=False)
    workdir = serializers.CharField(required=False)

    envs = KVPairsField(required=False)

    def create(self, validated_data):
        result = dict()
        envs_data = validated_data.pop('envs', None)
        result['executor'] = Executor(**validated_data)

        if envs_data is not None:
            result['envs'] = [Env(**env_data) for env_data in envs_data]
        return result


class MountPointSerializer(serializers.Serializer):
    filesystem_path = serializers.CharField()
    container_path = serializers.CharField()
    is_dir = serializers.BooleanField(required=False)
    is_input = serializers.BooleanField(required=False)

    def create(self, validated_data):
        return MountPoint(**validated_data)


class TaskSerializer(OmitEmptyValuesMixin, serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    status = serializers.CharField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)
    volumes = WritableStringRelatedField(many=True, required=False)
    tags = KVPairsField(required=False)

    executors = ExecutorSerializer(many=True)

    mount_points = MountPointSerializer(many=True, required=False)

    def validate_executors(self, executors):
        if len(executors) == 0:
            raise serializers.ValidationError('At lease one executor must be defined')
        return executors

    def create(self, validated_data: dict):
        result = dict()
        executors_data = validated_data.pop('executors')
        mount_points_data = validated_data.pop('mount_points', None)
        volumes_data = validated_data.pop('volumes', None)
        tags_data = validated_data.pop('tags', None)

        task = Task(**validated_data)
        result['task'] = task

        # Re-instantiating the serializers because DRF things
        executors_serializer = ExecutorSerializer(many=True)
        executors = executors_serializer.create(executors_data)
        result['executors'] = executors

        if mount_points_data is not None:
            mount_points_serializer = MountPointSerializer(many=True)
            mount_points = mount_points_serializer.create(mount_points_data)
            result['mount_points'] = mount_points

        if volumes_data is not None:
            volumes = [Volume(task=task, path=path) for path in volumes_data]
            result['volumes'] = volumes

        if tags_data is not None:
            tags = [Tag(**tag_data) for tag_data in tags_data]
            result['tags'] = tags

        return result


class TesExecutorSerializer(OmitEmptyValuesMixin, serializers.Serializer):
    command = serializers.JSONField()
    image = serializers.CharField()
    stderr = serializers.CharField()
    stdin = serializers.CharField()
    stdout = serializers.CharField()
    workdir = serializers.CharField()



class TesMountPointSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('get_url')
    path = serializers.CharField(source='container_path')
    type = serializers.SerializerMethodField('get_type')

    def __init__(self, *args, protocol: str = None, **kwargs):
        if protocol is None:
            raise ValueError(
                'Serializer keyword "protocol" for underlying file store needs to be defined during instantiation'
            )
        self.protocol = protocol
        super().__init__(*args, **kwargs)

    def get_url(self, instance: MountPoint):
        return f'{self.protocol}://{instance.filesystem_path}'

    def get_type(self, instance: MountPoint):
        return 'DIR' if instance.is_dir else 'FILE'


class TesTaskSerializer(OmitEmptyValuesMixin, serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    # executors = TesExecutorSerializer(required=False, many=True)
    # inputs = TesMountPointSerializer(required=False, many=True)
    # outputs = TesMountPointSerializer(required=False, many=True)
    # tags = KVPairsField(required=False)
    # volumes = WritableStringRelatedField(required=False)
