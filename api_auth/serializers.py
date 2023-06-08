from rest_framework import serializers


# Serializer naming convention: <ObjectType><Operation>Serializer
# Operations may be: List, Create, Details

class ParticipationListSerializer(serializers.Serializer):
    username = serializers.CharField(source='user.username')
    is_active = serializers.BooleanField(source='user.is_active')


class UserListSerializer(serializers.Serializer):
    username = serializers.CharField()
    is_active = serializers.BooleanField()


class UserListQPSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        [('any', 'All users'), ('active', 'Active users'), ('inactive', 'Inactive/banned users')], required=False)


class ParticipationCreateSerializer(UserListSerializer):
    is_active = None


class UserSerializer(UserListSerializer):
    fs_user_dir = serializers.CharField(required=False, source='profile.fs_user_dir')


class UserCreateSerializer(UserSerializer):
    pass


class UserDetailsSerializer(UserSerializer):
    pass


class UserUpdateSerializer(UserSerializer):
    username = None


class ContextListSerializer(serializers.Serializer):
    name = serializers.CharField()


class ContextSerializer(ContextListSerializer):
    max_tasks = serializers.IntegerField(required=False, source='quotas.max_tasks')
    max_ram_gb = serializers.IntegerField(required=False, source='quotas.max_ram_gb')
    max_active_tasks = serializers.IntegerField(required=False, source='quotas.max_active_tasks')
    max_cpu = serializers.IntegerField(required=False, source='quotas.max_cpu')
    max_process_time_seconds = serializers.IntegerField(required=False, source='quotas.max_process_time_seconds')


class ContextCreateSerializer(ContextSerializer):
    pass


class ContextUpdateSerializer(ContextCreateSerializer):
    name = None


class ContextDetailsSerializer(ContextCreateSerializer):
    users = UserListSerializer(many=True)


class ApiTokenListSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    title = serializers.CharField(required=False)
    hint = serializers.CharField(source='key')
    expiry = serializers.DateTimeField(required=False)
    is_active = serializers.BooleanField(read_only=True)


class ApiTokenListQPSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        [('any', 'All tokens'), ('active', 'Active tokens'), ('inactive', 'Revoked tokens')], required=False
    )


class ApiTokenSerializer(ApiTokenListSerializer):
    pass


class ApiTokenCreateSerializer(ApiTokenSerializer):
    uuid = None
    hint = None
    duration = serializers.CharField(required=False)


class ApiTokenDetailsSerializer(ApiTokenSerializer):
    created = serializers.DateTimeField()


class ApiTokenIssuedSerializer(ApiTokenDetailsSerializer):

    def get_token(self, obj):
        return self.context['token']

    token = serializers.SerializerMethodField('get_token')


class ApiTokenUpdateSerializer(ApiTokenCreateSerializer):
    duration = None
    extend_duration = serializers.CharField(required=False)
