from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from util.serializers import KVPairsField, LatestInstanceRelatedField, IntegerListField, SemverField
from workflows.models import WorkflowExecutorYield, WorkflowExecutor, WorkflowInputMountPoint, WorkflowOutputMountPoint, \
    WorkflowResourceSet, Workflow, WorkflowSpecification


class WorkflowExecutorYieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowExecutorYield
        exclude = ('executor','id')


class WorkflowExecutorSerializer(serializers.ModelSerializer):
    priority = serializers.FloatField(required=False, write_only=True)
    yields = WorkflowExecutorYieldSerializer(many=True, required=False)
    env = KVPairsField(required=False, child=serializers.CharField(allow_blank=True), allow_empty=False, source='envs')

    def validate_command(self, command):
        if not isinstance(command, list):
            raise ValidationError('Command must be a list of command tokens')
        return command

    class Meta:
        model = WorkflowExecutor
        exclude = ['workflow', 'id']


class WorkflowInputMountPointSerializer(serializers.ModelSerializer):

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
        return super(WorkflowInputMountPointSerializer, self).validate(data)

    class Meta:
        model = WorkflowInputMountPoint
        exclude = ['workflow', 'id']


class WorkflowOutputMountPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowOutputMountPoint
        exclude = ['workflow', 'id']


class WorkflowResourceSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowResourceSet
        exclude = ['workflow', 'id']


class WorkflowStatusLogSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, source='get_value_display')
    updated_at = serializers.DateTimeField(read_only=True, source='created_at')


class WorkflowsBasicListSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    state = LatestInstanceRelatedField(WorkflowStatusLogSerializer, ['-created_at'], source='status_logs')


class WorkflowsDetailedListSerializer(WorkflowsBasicListSerializer):
    context = serializers.CharField(source="context.name", read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)


class WorkflowsFullListSerializer(WorkflowsDetailedListSerializer):
    description = serializers.CharField()


class WorkflowsListQPSerializer(serializers.Serializer):
    view = serializers.ChoiceField(('basic', 'detailed', 'full'), required=False, default='basic')


class WorkflowSerializer(serializers.ModelSerializer):
    executors = WorkflowExecutorSerializer(many=True, allow_empty=False)
    inputs = WorkflowInputMountPointSerializer(many=True, allow_empty=False, required=False)
    outputs = WorkflowOutputMountPointSerializer(many=True, allow_empty=False, required=False)
    resources = WorkflowResourceSetSerializer(required=False)
    state = WorkflowStatusLogSerializer(many=True, read_only=True, source='status_logs')
    execution_order = IntegerListField(required=False)

    class Meta:
        model = Workflow
        read_only_fields = ['uuid']
        exclude = ['backend_ref', 'id', 'user', 'context']

    def validate_execution_order(self, execution_order):
        if any(filter(lambda idx: idx>=len(self.initial_data['executors']), eval(execution_order))):
            raise ValidationError(
                detail='Provided execution order references a non-existent executor\'s index'
            )
        return execution_order


class WorkflowSpecificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkflowSpecification
        exclude = ['workflow', 'id']
