from rest_framework import serializers

from util.serializers import SemverField


class WorkflowManagerLanguageSerializer(serializers.Serializer):
    language = serializers.CharField()
    versions = SemverField(default='*')

class WorkflowManagerSerializer(serializers.Serializer):
    languages = WorkflowManagerLanguageSerializer(many=True, required=False, allow_empty=False)
    use_definition = serializers.BooleanField(default=False)

class ManagerConfigurationSerializer(serializers.Serializer):
    delegate_tasks = serializers.BooleanField(default=False)
    workflows = WorkflowManagerSerializer(required=False)


class ManagerSerializer(serializers.Serializer):
    name = serializers.CharField()
    class_path = serializers.CharField()
    enabled = serializers.BooleanField(default=True)
    configuration = ManagerConfigurationSerializer(required=False)


class ManagerConfigFileSerializer(serializers.Serializer):
    managers = ManagerSerializer(many=True, allow_empty=False, required=False)

    def validate(self, attrs):
        validated = super(ManagerConfigFileSerializer, self).validate(attrs)

        manager_names = [m['name'] for m in attrs['managers']]
        manager_unique_names = set(manager_names)
        if len(manager_unique_names) < len(manager_names):
            for name in manager_unique_names:
                manager_names.remove(name)
            raise serializers.ValidationError(f'A manager with a duplicate name was found: {manager_names[0]}')

        return validated
