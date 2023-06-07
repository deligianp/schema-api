from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.services import ContextService, ParticipationService
from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsApplicationService, IsActive
from api_auth.serializers import ContextListSerializer, ContextCreateSerializer, ContextDetailsSerializer, \
    ContextUpdateSerializer, ContextSerializer, UserListSerializer, UserCreateSerializer, UserSerializer, \
    UserDetailsSerializer, UserUpdateSerializer, ParticipationListSerializer, ParticipationCreateSerializer, \
    ApiTokenListSerializer, ApiTokenCreateSerializer, ApiTokenIssuedSerializer, ApiTokenDetailsSerializer, \
    ApiTokenUpdateSerializer, ApiTokenSerializer, ApiTokenListQPSerializer, UserListQPSerializer
from api_auth.services import AuthEntityService, ApiTokenService


class ContextsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request):
        application_service = request.user
        context_service = ContextService(application_service)
        contexts = context_service.get_contexts()
        context_list_serializer = ContextListSerializer(contexts, many=True)
        return Response(data=context_list_serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ContextCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.create_context(**serializer.validated_data)

        context_serializer = ContextSerializer(context)
        return Response(status=status.HTTP_201_CREATED, data=context_serializer.data)


class ContextDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, name):
        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)
        context_details_serializer = ContextDetailsSerializer(context)
        return Response(status=status.HTTP_200_OK, data=context_details_serializer.data)

    def patch(self, request, name):
        serializer = ContextUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        output_data = {}
        if serializer.validated_data:
            # Use this for partial updates that no update values have been given
            application_service = request.user
            context_service = ContextService(application_service)
            context = context_service.update_context(update_values=serializer.validated_data, name=name)
            context_serializer = ContextSerializer(context)
            output_data = context_serializer.data
        return Response(status=status.HTTP_202_ACCEPTED, data=output_data)


class UsersAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request):
        qp_serializer = UserListQPSerializer(data=request.query_params)
        qp_serializer.is_valid(raise_exception=True)
        query_params = qp_serializer.validated_data

        application_service = request.user
        auth_entity_service = AuthEntityService(application_service)
        users = auth_entity_service.get_users()
        if 'status' in query_params and query_params['status'] != 'any':
            users = users.filter(is_active=query_params['status'] == 'active')
        user_list_serializer = UserListSerializer(users, many=True)
        return Response(data=user_list_serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application_service = request.user
        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.create_user(**serializer.validated_data)

        user_serializer = UserSerializer(user)
        return Response(status=status.HTTP_201_CREATED, data=user_serializer.data)


class UserDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, username):
        application_service = request.user
        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)
        user_details_serializer = UserDetailsSerializer(user)
        return Response(status=status.HTTP_200_OK, data=user_details_serializer.data)

    def patch(self, request, username):
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        output_data = {}
        if serializer.validated_data:
            # Use this for partial updates that no update values have been given
            application_service = request.user
            auth_entity_service = AuthEntityService(application_service)
            user = auth_entity_service.update_user(update_values=serializer.validated_data, username=username)
            user_serializer = UserSerializer(user)
            output_data = user_serializer.data
        return Response(status=status.HTTP_202_ACCEPTED, data=output_data)


class ContextParticipantsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, name):
        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)
        participation_service = ParticipationService(context)
        participations = participation_service.get_participations()
        participation_list_serializer = ParticipationListSerializer(participations, many=True)
        return Response(data=participation_list_serializer.data, status=status.HTTP_200_OK)

    def post(self, request, name):
        serializer = ParticipationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application_service = request.user
        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(**serializer.validated_data)

        context_service = ContextService(application_service)
        context = context_service.assign_user(user, name=name)

        context_details_serializer = ContextDetailsSerializer(context)
        return Response(status=status.HTTP_201_CREATED, data=context_details_serializer.data)


class ContextParticipantDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def delete(self, request, name, username):
        application_service = request.user

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        context_service = ContextService(application_service)
        context = context_service.remove_user(user, name=name)

        context_details_serializer = ContextDetailsSerializer(context)
        return Response(status=status.HTTP_204_NO_CONTENT, data=context_details_serializer.data)


class ContextParticipationTokensAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, name, username):
        application_service = request.user

        qp_serializer = ApiTokenListQPSerializer(data=request.query_params)
        qp_serializer.is_valid(raise_exception=True)
        query_params = qp_serializer.validated_data

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        api_token_service = ApiTokenService(user, context=context)
        tokens = api_token_service.get_tokens()
        if 'status' in query_params and query_params['status'] != 'any':
            tokens = tokens.filter(is_active=query_params['status'] == 'active')
        api_token_list_serializer = ApiTokenListSerializer(tokens, many=True)
        return Response(data=api_token_list_serializer.data, status=status.HTTP_200_OK)

    def post(self, request, name, username):
        serializer = ApiTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application_service = request.user

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        api_token_service = ApiTokenService(user, context=context)
        secret, api_token = api_token_service.issue_token(**serializer.validated_data)

        api_token_issued_serializer = ApiTokenIssuedSerializer(api_token, context={'token': secret})
        return Response(status=status.HTTP_201_CREATED, data=api_token_issued_serializer.data)


class ContextParticipationTokenDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, name, username, uuid):
        application_service = request.user

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        api_token_service = ApiTokenService(user, context=context)
        api_token = api_token_service.get_token(uuid)

        api_token_details_serializer = ApiTokenDetailsSerializer(api_token)
        return Response(status=status.HTTP_200_OK, data=api_token_details_serializer.data)

    def patch(self, request, name, username, uuid):
        serializer = ApiTokenUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        output_data = {}
        if serializer.validated_data:
            # Use this for partial updates that no update values have been given

            application_service = request.user

            context_service = ContextService(application_service)
            context = context_service.get_context(name=name)

            auth_entity_service = AuthEntityService(application_service)
            user = auth_entity_service.get_user(username=username)

            api_token_service = ApiTokenService(user, context=context)

            api_token = api_token_service.update_token(update_values=serializer.validated_data, token_uuid=uuid)
            api_token_serializer = ApiTokenSerializer(api_token)
            output_data = api_token_serializer.data
        return Response(status=status.HTTP_202_ACCEPTED, data=output_data)

    def delete(self, request, name, username, uuid):
        application_service = request.user

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        api_token_service = ApiTokenService(user, context=context)
        api_token_service.revoke_token(token_uuid=uuid)

        return Response(status=status.HTTP_204_NO_CONTENT)
