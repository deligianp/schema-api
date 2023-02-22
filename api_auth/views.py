from datetime import datetime

from django.contrib.auth.models import User
from django.db import IntegrityError
# Create your views here.
from knox.auth import TokenAuthentication
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api_auth.models import ApiAuthToken
from api_auth.permissions import IsContextManager
from api_auth.services import ContextManagerService
from api_auth.utils import denamespace, namespace, get_primary_validation_error_message


class ContextAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsContextManager]

    class InputSerializer(serializers.Serializer):
        context = serializers.SlugField()
        limits_url = serializers.URLField(required=False)

    class OutputSerializer(serializers.Serializer):
        context = serializers.SerializerMethodField(source='context_name')

        def get_context(self, user):
            return denamespace(user.username)[1]

    def get(self, request):
        context_manager_service = ContextManagerService(context_manager=request.user)
        contexts = context_manager_service.get_contexts()
        output_serializer = self.OutputSerializer(contexts, many=True)
        return Response(data=output_serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        input_serializer = self.InputSerializer(data=request.data)
        try:
            input_serializer.is_valid(raise_exception=True)
        except DRFValidationError as drf_ve:
            msg = get_primary_validation_error_message(drf_ve)
            return Response(data={'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

        context_manager_service = ContextManagerService(context_manager=request.user)
        context_name = input_serializer.validated_data["context"]
        limits_url = input_serializer.validated_data.get("limits_url", None)
        try:
            context_manager_service.register_context(
                namespace(request.user.username, context_name),
                limits_url
            )
        except IntegrityError:
            # Case when context name already exists
            return Response(data={'detail': f'A context named "{context_name}" already exists'},
                            status=status.HTTP_409_CONFLICT)

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
        try:
            context = context_manager_service.get_context(namespace(request.user.username, context_name))
        except User.DoesNotExist:
            return Response(data={'detail': f'No context with name "{context_name}" exists'},
                            status=status.HTTP_404_NOT_FOUND)
        context_serializer = self.OutputSerializer(context)
        return Response(data=context_serializer.data, status=status.HTTP_200_OK)


class ContextTokenAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsContextManager]

    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        expiry = serializers.DateTimeField(required=False)

    class OutputMinimalSerializer(serializers.Serializer):
        uuid = serializers.UUIDField(source='uuid_ref')

    class OutputDetailedSerializer(OutputMinimalSerializer):
        title = serializers.CharField()
        hint = serializers.CharField(source='token_key')
        expiry = serializers.DateTimeField()

    def get(self, request, context_name):
        token_status = request.query_params.get('status', 'active').lower()
        result_view = request.query_params.get('view', 'minimal').lower()
        context_manager_service = ContextManagerService(context_manager=request.user)
        context_name = namespace(request.user.username, context_name)
        try:
            if token_status == 'active':
                api_auth_tokens = context_manager_service.get_active_context_tokens(context_name)
            elif token_status == 'expired':
                api_auth_tokens = context_manager_service.get_expired_context_tokens(context_name)
            elif token_status == 'all':
                api_auth_tokens = context_manager_service.get_context_tokens(context_name=namespace(context_name))
            else:
                return Response(data={
                    'detail': 'Invalid value for query parameter status. Acceptable values are: active, expired, all'
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response(data={
                'detail': f'No context with name "{context_name}" exists'
            }, status=status.HTTP_404_NOT_FOUND)

        if result_view == 'full':
            output_serializer = self.OutputDetailedSerializer(api_auth_tokens, many=True)
        elif result_view == 'minimal':
            output_serializer = self.OutputMinimalSerializer(api_auth_tokens, many=True)
        else:
            return Response(data={
                'detail': 'Invalid value for query parameter "view". Acceptable values are: minimal, full'
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(data=output_serializer.data, status=status.HTTP_200_OK)

    def post(self, request, context_name):
        input_serializer = self.InputSerializer(data=request.data)
        try:
            input_serializer.is_valid(raise_exception=True)
        except DRFValidationError as drf_ve:
            msg = get_primary_validation_error_message(drf_ve)
            return Response(data={'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

        context_manager_service = ContextManagerService(context_manager=request.user)
        try:
            token = context_manager_service.issue_context_token(namespace(request.user.username, context_name),
                                                                **input_serializer.validated_data)
        except User.DoesNotExist:
            return Response(data={
                'detail': f'No context with name "{context_name}" exists'
            }, status=status.HTTP_404_NOT_FOUND)

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
        try:
            api_auth_token = context_manager_service.get_context_token(namespace(request.user.username, context_name),
                                                                       token_uuid)
        except User.DoesNotExist:
            return Response(data={
                'detail': f'No context with name "{context_name}" exists'
            }, status=status.HTTP_404_NOT_FOUND)
        except ApiAuthToken.DoesNotExist:
            return Response(data={
                'detail': f'No API key with a UUID of "{token_uuid}" exists, in the context of "{context_name}"'
            }, status=status.HTTP_404_NOT_FOUND)

        input_serializer = self.InputSerializer(api_auth_token, data=request.data, partial=True)
        try:
            input_serializer.is_valid(raise_exception=True)
        except DRFValidationError as drf_ve:
            msg = get_primary_validation_error_message(drf_ve)
            return Response(data={'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

        try:
            context_manager_service.update_context_token(namespace(request.user.username, context_name), token_uuid,
                                                         **input_serializer.validated_data)
        except User.DoesNotExist:
            return Response(data={
                'detail': f'No context with name "{context_name}" exists'
            }, status=status.HTTP_404_NOT_FOUND)
        except ApiAuthToken.DoesNotExist:
            return Response(data={
                'detail': f'No API key with a UUID of "{token_uuid}" exists, in the context of "{context_name}"'
            }, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, context_name, token_uuid):
        context_manager_service = ContextManagerService(context_manager=request.user)
        try:
            context_manager_service.delete_context_token(namespace(request.user.username, context_name), token_uuid)
        except User.DoesNotExist:
            return Response(data={
                'detail': f'No context with name "{context_name}" exists'
            }, status=status.HTTP_404_NOT_FOUND)
        except ApiAuthToken.DoesNotExist:
            return Response(data={
                'detail': f'No API key with a UUID of "{token_uuid}" exists, in the context of "{context_name}"'
            }, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_200_OK)

    def get(self, request, context_name, token_uuid):
        context_manager_service = ContextManagerService(context_manager=request.user)
        try:
            api_auth_token = context_manager_service.get_context_token(namespace(request.user.username, context_name),
                                                                       token_uuid)
        except User.DoesNotExist:
            return Response(data={
                'detail': f'No context with name "{context_name}" exists'
            }, status=status.HTTP_404_NOT_FOUND)
        except ApiAuthToken.DoesNotExist:
            return Response(data={
                'detail': f'No API key with a UUID of "{token_uuid}" exists, in the context of "{context_name}"'
            }, status=status.HTTP_404_NOT_FOUND)
        output_serializer = self.OutputSerializer(api_auth_token)
        return Response(data=output_serializer.data, status=status.HTTP_200_OK)
