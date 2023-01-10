import uuid
from datetime import datetime

from django.contrib.auth.models import User
from django.shortcuts import render

# Create your views here.
from knox.auth import TokenAuthentication
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer
from rest_framework.views import APIView

from api_auth.models import ServiceProfile
from api_auth.permissions import IsContextManager
from api_auth.services import ContextManagerService, AuthService
from api_auth.utils import denamespace, namespace


class TokenListEndpoint(APIView):
    class OutputSerializer(serializers.Serializer):
        pass
        # uuid
        # key
        # title
        # expired
        # expiry

    def get(self, request):
        username = ''
        user = request.user
        service_profile = ServiceProfile.objects.get(service_data=user)
        context_manager_service = ContextManagerService(service_profile)

        tokens = context_manager_service.get_context_tokens(username)
        return Response(status=status.HTTP_200_OK)


class ContextAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsContextManager]

    class InputSerializer(serializers.Serializer):
        context = serializers.SlugField()

    def get(self, request):
        context_manager_service = ContextManagerService(context_manager=request.user)
        contexts = context_manager_service.get_contexts()
        return Response(data=[denamespace(context.username)[1] for context in contexts], status=status.HTTP_200_OK)

    def post(self, request):
        input_serializer = self.InputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        context_manager_service = ContextManagerService(context_manager=request.user)

        context_manager_service.register_context(
            namespace(request.user.username, input_serializer.validated_data["context"])
        )

        return Response(status=status.HTTP_201_CREATED)


class ContextDetailsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsContextManager]

    class OutputSerializer(serializers.Serializer):
        context = serializers.SerializerMethodField(source='context_name')
        time_registered = serializers.DateTimeField(source='date_joined')
        num_issued_tokens = serializers.SerializerMethodField()

        def get_context(self, user):
            return denamespace(user.username)[1]

        def get_num_issued_tokens(self, user):
            return user.auth_token_set.filter(expiry__gte=datetime.now()).count()

    def get(self, request, context_name):
        context_manager_service = ContextManagerService(context_manager=request.user)
        context = context_manager_service.get_context(namespace(request.user.username, context_name))
        context_serializer = self.OutputSerializer(context)
        return Response(data=context_serializer.data, status=status.HTTP_200_OK)


class ContextTokenAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsContextManager]

    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        expiry = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField(source='uuid_ref')
        title = serializers.CharField()
        hint = serializers.CharField(source='token_key')
        expiry = serializers.DateTimeField()

    def get(self, request, context_name):
        token_status = request.query_params.get('status', 'active').lower()
        context_manager_service = ContextManagerService(context_manager=request.user)
        context_name = namespace(request.user.username, context_name)
        if token_status == 'active':
            api_auth_tokens = context_manager_service.get_active_context_tokens(context_name)
        elif token_status == 'expired':
            api_auth_tokens = context_manager_service.get_expired_context_tokens(context_name)
        elif token_status == 'all':
            api_auth_tokens = context_manager_service.get_context_tokens(context_name=namespace(context_name))
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        output_serializer = self.OutputSerializer(api_auth_tokens, many=True)
        return Response(data=output_serializer.data, status=status.HTTP_200_OK)

    def post(self, request, context_name):
        input_serializer = self.InputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        context_manager_service = ContextManagerService(context_manager=request.user)
        token = context_manager_service.issue_context_token(namespace(request.user.username, context_name),
                                                            **input_serializer.validated_data)

        return Response(data={"token": token}, status=status.HTTP_201_CREATED)


class ContextTokenDetailsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsContextManager]

    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        expiry = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField(source='uuid_ref')
        title = serializers.CharField()
        hint = serializers.CharField(source='token_key')
        expiry = serializers.DateTimeField()

    def patch(self, request, context_name, token_uuid):
        context_manager_service = ContextManagerService(context_manager=request.user)
        api_auth_token = context_manager_service.get_context_token(namespace(request.user.username, context_name),
                                                                   token_uuid)

        input_serializer = self.InputSerializer(api_auth_token, data=request.data, partial=True)
        input_serializer.is_valid(raise_exception=True)

        context_manager_service.update_context_token(namespace(request.user.username, context_name), token_uuid,
                                                     **input_serializer.validated_data)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, context_name, token_uuid):
        context_manager_service = ContextManagerService(context_manager=request.user)
        context_manager_service.delete_context_token(namespace(request.user.username, context_name), token_uuid)
        return Response(status=status.HTTP_200_OK)

    def get(self, request, context_name, token_uuid):
        context_manager_service = ContextManagerService(context_manager=request.user)
        api_auth_token = context_manager_service.get_context_token(namespace(request.user.username, context_name),
                                                                   token_uuid)
        output_serializer = self.OutputSerializer(api_auth_token)
        return Response(data=output_serializer.data, status=status.HTTP_200_OK)
