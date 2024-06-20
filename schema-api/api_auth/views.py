import logging

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.services import ContextService, ParticipationService
from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsApplicationService, IsActive
from api_auth.serializers import ContextListSerializer, ContextCreateSerializer, ContextDetailsSerializer, \
    ContextUpdateSerializer, ContextSerializer, UserListSerializer, \
    UserDetailsSerializer, UserUpdateSerializer, ParticipationListSerializer, \
    ApiTokenListSerializer, ApiTokenCreateSerializer, ApiTokenIssuedSerializer, ApiTokenDetailsSerializer, \
    ApiTokenUpdateSerializer, ApiTokenSerializer, ApiTokenListQPSerializer, UserListQPSerializer, UserSerializer
from api_auth.services import AuthEntityService, ApiTokenService
from quotas.serializers import QuotasSerializer
from quotas.services import QuotasService

logger = logging.getLogger(__name__)


class ContextsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    @extend_schema(
        summary='List created contexts',
        description='Retrieve the list of contexts created by the authenticated application service',
        tags=['Contexts'],
        responses={
            200: OpenApiResponse(
                description='List of contexts retrieved',
                response=ContextListSerializer(many=True),
                examples=[
                    OpenApiExample(
                        'valid-list-contexts-0',
                        summary='List of created contexts',
                        value={
                            'name': 'context0'
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            )
        }
    )
    def get(self, request):
        application_service = request.user
        context_service = ContextService(application_service)
        contexts = context_service.get_contexts()
        context_list_serializer = ContextListSerializer(contexts, many=True)
        return Response(data=context_list_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Create new context',
        description='Create a new context with the provided `name` and quotas, for the authenticated application '
                    'service',
        tags=['Contexts'],
        request=ContextCreateSerializer,
        examples=[
            OpenApiExample(
                'valid-create-context-request-0',
                summary='Create context named `context0` with some quotas',
                value={
                    'name': 'context0',
                    'max_tasks': 1,
                    'max_cpu': 1,
                    'max_ram_gb': 4,
                    'max_active_tasks': 1,
                    'max_process_time_seconds': 600
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            201: OpenApiResponse(
                description='Context successfully created',
                response=ContextSerializer,
                examples=[
                    OpenApiExample(
                        'valid-create-context-0',
                        summary='Response for creating a context named `context0`',
                        value={
                            'name': 'context0',
                            'max_tasks': 1,
                            'max_cpu': 1,
                            'max_ram_gb': 4,
                            'max_active_tasks': 1,
                            'max_process_time_seconds': 600
                        },
                        request_only=False,
                        response_only=True,
                    ),
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid request body'
            ),
            409: OpenApiResponse(
                description='A context with the given context `name` already exists'
            )
        }
    )
    def post(self, request):
        serializer = ContextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.create_context(**serializer.validated_data)

        context_serializer = ContextSerializer(context)
        return Response(status=status.HTTP_201_CREATED, data=context_serializer.data)


class ContextDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    @extend_schema(
        summary='Get context details',
        description='Get details for a context with the given context `name`, along with users assigned to this '
                    'context',
        tags=['Contexts'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN)
        ],
        responses={
            200: OpenApiResponse(
                description='Context successfully retrieved',
                response=ContextDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-retrieve-context-0',
                        summary='Retrieved "context0" with assigned user "user0"',
                        value={
                            'name': 'context0',
                            'max_tasks': 1,
                            'max_cpu': 1,
                            'max_ram_gb': 4,
                            'max_active_tasks': 1,
                            'max_process_time_seconds': 600,
                            'users': [
                                {
                                    'username': 'user0'
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    ),
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameter'
            ),
            404: OpenApiResponse(
                description='No context was found with the given context `name`'
            )
        }
    )
    def get(self, request, name):
        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)
        context_details_serializer = ContextDetailsSerializer(context)
        return Response(status=status.HTTP_200_OK, data=context_details_serializer.data)

    @extend_schema(
        summary='Update context',
        description='Update context quotas',
        tags=['Contexts'],
        request=ContextUpdateSerializer,
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN)
        ],
        examples=[
            OpenApiExample(
                'valid-update-context-request-0',
                summary='Update subset of quotas',
                value={
                    'max_active_tasks': 1234
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-update-context-request-1',
                summary='Update all quotas',
                value={
                    'max_tasks': 2,
                    'max_cpu': 3,
                    'max_ram_gb': 6,
                    'max_active_tasks': 2345,
                    'max_process_time_seconds': 3600
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            202: OpenApiResponse(
                description='Context quotas successfully updated',
                response=ContextSerializer,
                examples=[
                    OpenApiExample(
                        'valid-update-context-0',
                        summary='Context "context0\'s" max_active_tasks updated',
                        value={
                            'name': 'context0',
                            'max_tasks': 1,
                            'max_cpu': 1,
                            'max_ram_gb': 4,
                            'max_active_tasks': 1234,
                            'max_process_time_seconds': 600
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'valid-update-context-1',
                        summary='Context "context0\'s" all quotas updated',
                        value={
                            'name': 'context0',
                            'max_tasks': 2,
                            'max_cpu': 3,
                            'max_ram_gb': 6,
                            'max_active_tasks': 2345,
                            'max_process_time_seconds': 3600
                        },
                        request_only=False,
                        response_only=True,
                    ),
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameter or request body'
            ),
            404: OpenApiResponse(
                description='No context was found with the given context `name`'
            ),
            409: OpenApiResponse(
                description='A context with the given context `name` already exists'
            )
        }
    )
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


class ContextQuotasAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, name):
        application_service = request.user
        logger.info(f'Request of application service "{application_service.username}" to retrieve quotas for context '
                    f'named "{name}"')

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)
        quotas_service = QuotasService(context)
        quotas = quotas_service.get_quotas()

        quotas_serializer = QuotasSerializer(quotas)
        return Response(status=status.HTTP_200_OK, data=quotas_serializer.data)

    def patch(self, request, name):
        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        quotas_serializer = QuotasSerializer(data=request.data)
        quotas_serializer.is_valid(raise_exception=True)

        quotas_service = QuotasService(context)
        quotas = quotas_service.set_quotas(**quotas_serializer.validated_data)

        quotas_serializer = QuotasSerializer(quotas)
        return Response(status=status.HTTP_202_ACCEPTED, data=quotas_serializer.data)

    def delete(self, request, name):
        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)
        quotas_service = QuotasService(context)
        quotas_service.unset_quotas()

        return Response(status=status.HTTP_204_NO_CONTENT)


class UsersAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    @extend_schema(
        summary='List users',
        description='Retrieve the list of users created by the authenticated application service',
        tags=['Users'],
        parameters=[UserListQPSerializer],
        responses={
            200: OpenApiResponse(
                description='List of users retrieved',
                response=UserListSerializer(many=True),
                examples=[
                    OpenApiExample(
                        'valid-list-users-0',
                        summary='List of users',
                        value={
                            'username': 'user0',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid query parameters'
            )
        }
    )
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

    @extend_schema(
        summary='Create new user',
        description='Create a new user with the provided username, for the authenticated application service',
        tags=['Users'],
        request=UserDetailsSerializer,
        examples=[
            OpenApiExample(
                'valid-create-user-request-0',
                summary='Create user with username "user0"',
                value={
                    'username': 'user0'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-create-user-request-1',
                summary='Create user with username "user0" and fs_user_dir "user0-alt',
                value={
                    'username': 'user0',
                    'fs_user_dir': 'user0-alt'
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            201: OpenApiResponse(
                description='User successfully created',
                response=UserDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-create-user-0',
                        summary='Created user with username "user0" and default fs_user_dir "user0"',
                        value={
                            'username': 'user0',
                            'fs_user_dir': 'user0',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'valid-create-user-1',
                        summary='Created user with username "user0" and fs_user_dir "user0-alt"',
                        value={
                            'username': 'user0',
                            'fs_user_dir': 'user0-alt',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    ),
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid request body'
            ),
            409: OpenApiResponse(
                description='Potential causes:\n'
                            '- A user with the given `username` already exists\n'
                            '- User\'s `fs_user_dir` is allocated to a different user'
            )
        }
    )
    def post(self, request):
        serializer = UserDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application_service = request.user
        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.create_user(**serializer.validated_data)

        user_serializer = UserDetailsSerializer(user)
        return Response(status=status.HTTP_201_CREATED, data=user_serializer.data)


class UserDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    @extend_schema(
        summary='Get user details',
        description='Get details for a user with the given username',
        tags=['Users'],
        parameters=[
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN)
        ],
        responses={
            200: OpenApiResponse(
                description='User successfully retrieved',
                response=UserDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-retrieve-user-0',
                        summary='Retrieved user "user0"',
                        value={
                            'username': 'user0',
                            'fs_user_dir': 'user0',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    ),
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameter'
            ),
            404: OpenApiResponse(
                description='No context was found with the given `username`'
            )
        }
    )
    def get(self, request, username):
        application_service = request.user
        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)
        user_details_serializer = UserDetailsSerializer(user)
        return Response(status=status.HTTP_200_OK, data=user_details_serializer.data)

    @extend_schema(
        summary='Update user',
        description='Update user file system home directory',
        tags=['Users'],
        request=UserUpdateSerializer,
        parameters=[
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN)
        ],
        examples=[
            OpenApiExample(
                'valid-update-user-request-0',
                summary='Update fs_user_dir',
                value={
                    'fs_user_dir': 'user0-alt'
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            202: OpenApiResponse(
                description='User\'s file system home directory successfully updated',
                response=UserDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-update-user-0',
                        summary='User "user0\'s" fs_user_dir updated',
                        value={
                            'username': 'user0',
                            'fs_user_dir': 'user0',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameter or request body'
            ),
            404: OpenApiResponse(
                description='No user was found with the given username'
            ),
            409: OpenApiResponse(
                description='Updated fs_user_dir is allocated to a different user'
            )
        }
    )
    def patch(self, request, username):
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        output_data = {}
        if serializer.validated_data:
            # Use this for partial updates that no update values have been given
            application_service = request.user
            auth_entity_service = AuthEntityService(application_service)
            user = auth_entity_service.update_user(update_values=serializer.validated_data, username=username)
            user_serializer = UserDetailsSerializer(user)
            output_data = user_serializer.data
        return Response(status=status.HTTP_202_ACCEPTED, data=output_data)


class ContextParticipantsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    @extend_schema(
        summary='List users assigned to a context',
        description='Retrieve the list of users currently assigned the context referenced by the `name` path parameter',
        tags=['Context participants'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN)
        ],
        responses={
            200: OpenApiResponse(
                description='List of context\'s users retrieved',
                response=ParticipationListSerializer(many=True),
                examples=[
                    OpenApiExample(
                        'valid-list-participants-0',
                        summary='List of context\'s participants',
                        value={
                            'username': 'user0',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            404: OpenApiResponse(
                description='No context was found with the given context `name`'
            )
        }
    )
    def get(self, request, name):
        application_service = request.user
        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)
        participation_service = ParticipationService(context)
        participations = participation_service.get_participations()
        participation_list_serializer = ParticipationListSerializer(participations, many=True)
        return Response(data=participation_list_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Assign a user to a context',
        description='Assign a user to the context referenced by the `name` path parameter',
        tags=['Context participants'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN)
        ],
        request=UserSerializer,
        examples=[
            OpenApiExample(
                'valid-assign-participant-request-0',
                summary='Assign user with username "user0"',
                value={
                    'username': 'user0'
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            201: OpenApiResponse(
                description='User successfully assigned to the referenced context',
                response=ContextDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-assign-participant-0',
                        summary='Assigned user with username "user0" to context with name "context0"',
                        value={
                            'name': 'context0',
                            'max_tasks': 1,
                            'max_cpu': 1,
                            'max_ram_gb': 4,
                            'max_active_tasks': 1,
                            'max_process_time_seconds': 600,
                            'users': [
                                {
                                    'username': 'user0'
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameter or request body'
            ),
            404: OpenApiResponse(
                description='No context was found with the given context `name`'
            ),
            409: OpenApiResponse(
                description='User is already assigned to the referenced context'
            )
        }
    )
    def post(self, request, name):
        serializer = UserSerializer(data=request.data)
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

    @extend_schema(
        summary='Remove user from context',
        description='Remove the user referenced by the `username` path parameter from the context referenced by the '
                    '`name` path parameter',
        tags=['Context participants'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN),
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN)
        ],
        responses={
            204: OpenApiResponse(
                description='Referenced user successfully removed from the referenced context',
                response=ContextDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-remove-participant-0',
                        summary='Removed user with username "user0" from context with name "context0"',
                        value={
                            'name': 'context0',
                            'max_tasks': 1,
                            'max_cpu': 1,
                            'max_ram_gb': 4,
                            'max_active_tasks': 1,
                            'max_process_time_seconds': 600,
                            'users': []
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameters'
            ),
            404: OpenApiResponse(
                description='Potential causes:\n'
                            '- No context was found with the referenced context `name`\n'
                            '- No user was found with the referenced `username`\n'
                            '- User with the referenced `username` is not assigned to context with the referenced '
                            'context `name`'
            )
        }
    )
    def delete(self, request, name, username):
        application_service = request.user

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        context_service = ContextService(application_service)
        context = context_service.remove_user(user, name=name)

        context_details_serializer = ContextDetailsSerializer(context)
        return Response(status=status.HTTP_204_NO_CONTENT, data=context_details_serializer.data)


class ContextParticipantQuotasAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request, name, username):
        application_service = request.user
        logger.info(f'Request of application service "{application_service.username}" to retrieve quotas for user '
                    f'{username}, participating in context named "{name}"')

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        quotas_service = QuotasService(context, user)
        quotas = quotas_service.get_quotas()

        quotas_serializer = QuotasSerializer(quotas)
        return Response(status=status.HTTP_200_OK, data=quotas_serializer.data)

    def patch(self, request, name, username):
        application_service = request.user

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        quotas_serializer = QuotasSerializer(data=request.data)
        quotas_serializer.is_valid(raise_exception=True)

        quotas_service = QuotasService(context, user)
        quotas = quotas_service.set_quotas(**quotas_serializer.validated_data)

        quotas_serializer = QuotasSerializer(quotas)
        return Response(status=status.HTTP_202_ACCEPTED, data=quotas_serializer.data)

    def delete(self, request, name, username):
        application_service = request.user

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        quotas_service = QuotasService(context, user)
        quotas = quotas_service.unset_quotas()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ContextParticipationTokensAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    @extend_schema(
        summary='List context participation API tokens',
        description='Retrieve the list of tokens authenticating the participation of the user referenced by the '
                    '`username` path parameter, to the context referenced by the `name` path parameter',
        tags=['Context participation tokens'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN),
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN),
            ApiTokenListQPSerializer
        ],
        responses={
            200: OpenApiResponse(
                description='List of context participation tokens retrieved',
                response=ApiTokenListSerializer(many=True),
                examples=[
                    OpenApiExample(
                        'valid-list-participation-tokens-0',
                        summary='List of a context participation\'s tokens',
                        value={
                            'uuid': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                            'title': 'Token title',
                            'hint': 'abcdef01',
                            'expiry': '2025-04-03T02:01:00',
                            'is_active': True
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path or query parameters'
            ),
            404: OpenApiResponse(
                description='Potential causes:\n'
                            '- No context was found with the referenced context `name`\n'
                            '- No user was found with the referenced `username`\n'
                            '- User with the referenced `username` is not assigned to context with the referenced '
                            'context `name`'
            )
        }
    )
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

    @extend_schema(
        summary='Issue new context participation API token',
        description='Issue new API token authenticating the participation of the user referenced by the '
                    '`username` path parameter, to the context referenced by the `name` path parameter',
        tags=['Context participation tokens'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN),
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN)
        ],
        request=ApiTokenCreateSerializer,
        examples=[
            OpenApiExample(
                'valid-issue-participation-token-request-0',
                summary='Issue participation token only with duration',
                value={
                    'duration': '2 months'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-issue-participation-token-request-1',
                summary='Issue participation token only with expiry',
                value={
                    'expiry': '2024-04-03T02:01:00'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-issue-participation-token-request-2',
                summary='Issue participation token with title and duration',
                value={
                    'title': 'Token title',
                    'duration': '2 months'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-issue-participation-token-request-3',
                summary='Issue participation token with title and expiry',
                value={
                    'title': 'Token title',
                    'expiry': '2024-04-03T02:01:00'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-issue-participation-token-request-4',
                summary='Issue participation token with title and expiry, overriding duration',
                value={
                    'title': 'Token title',
                    'duration': '2 months',
                    'expiry': '2024-04-03T02:01:00'
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            201: OpenApiResponse(
                description='Context participation API token successfully issued. **NOTE:** `token` will only be '
                            'available through this response - the actual token value is not kept by the API - it is '
                            'each user\'s responsibility to safely store the API token for future use',
                response=ApiTokenIssuedSerializer,
                examples=[
                    OpenApiExample(
                        'valid-issue-participation-token-0',
                        summary='Issued context participation API token',
                        value={
                            'uuid': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                            'title': 'Token title',
                            'hint': 'abcdef01',
                            'expiry': '2025-04-03T02:01:00',
                            'is_active': True,
                            'created': '2023-01-01T00:00:00',
                            'token': 'abcdef01abcdef01abcdef01abcdef01abcdef01abcdef01abcdef01abcdef01abcdef01abcdef01'
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameter or request body'
            ),
            404: OpenApiResponse(
                description='Potential causes:\n'
                            '- No context was found with the referenced context `name`\n'
                            '- No user was found with the referenced `username`\n'
                            '- User with the referenced `username` is not assigned to context with the referenced '
                            'context `name`'
            )
        }
    )
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

    @extend_schema(
        summary='Get context participation API token\'s details',
        description='Get details of the API token referenced by the `uuid` path parameter and authenticating the '
                    'participation of the user referenced by the `username` path parameter, to the context referenced '
                    'by the `name` path parameter',
        tags=['Context participation tokens'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN),
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN),
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of an issued context participation API token', required=True,
                             allow_blank=False, many=False)
        ],
        responses={
            200: OpenApiResponse(
                description='Context participation API token successfully retrieved',
                response=ApiTokenDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-retrieve-participation-token-0',
                        summary='Retrieved context participation API token',
                        value={
                            'uuid': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                            'title': 'Token title',
                            'hint': 'abcdef01',
                            'expiry': '2025-04-03T02:01:00',
                            'is_active': True,
                            'created': '2023-01-01T00:00:00'
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameters'
            ),
            404: OpenApiResponse(
                description='Potential causes:\n'
                            '- No context was found with the referenced context `name`\n'
                            '- No user was found with the referenced `username`\n'
                            '- User with the referenced `username` is not assigned to context with the referenced '
                            'context `name`\n'
                            '- No context participation API token was found with the given `uuid`, for the '
                            'participation of the user referenced with `username`, to the context referenced with '
                            '`name`'
            )
        }
    )
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

    @extend_schema(
        summary='Update context participation API token',
        description='Update context participation API token referenced by the `uuid` path parameter and authenticating '
                    'the participation of the user referenced by the `username` path parameter, to the context '
                    'referenced by the `name` path parameter',
        tags=['Context participation tokens'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN),
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN),
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of an issued context participation API token', required=True,
                             allow_blank=False, many=False)
        ],
        request=ApiTokenUpdateSerializer,
        examples=[
            OpenApiExample(
                'valid-update-participation-token-request-0',
                summary='Update participation token\'s title',
                value={
                    'title': 'New token title'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-update-participation-token-request-1',
                summary='Extend participation token\'s expiry by a certain duration',
                value={
                    'extend_duration': '2 months'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-update-participation-token-request-2',
                summary='Update participation token\'s expiry to a certain timestamp',
                value={
                    'expiry': '2024-04-03T02:01:00'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-update-participation-token-request-3',
                summary='Update participation token\'s title extend expiry by a certain duration',
                value={
                    'title': 'New token title',
                    'extend_duration': '2 months'
                },
                request_only=True,
                response_only=False
            ),
            OpenApiExample(
                'valid-update-participation-token-request-4',
                summary='Update participation token\'s title and expiry, overriding extend_duration',
                value={
                    'title': 'New token title',
                    'extend_duration': '2 months',
                    'expiry': '2024-04-03T02:01:00'
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            202: OpenApiResponse(
                description='Context participation API token successfully updated',
                response=ApiTokenDetailsSerializer,
                examples=[
                    OpenApiExample(
                        'valid-update-participation-token-0',
                        summary='Updated context participation API token',
                        value={
                            'uuid': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                            'title': 'Token title',
                            'hint': 'abcdef01',
                            'expiry': '2025-04-03T02:01:00',
                            'is_active': True,
                            'created': '2023-01-01T00:00:00'
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameters or request body'
            ),
            404: OpenApiResponse(
                description='Potential causes:\n'
                            '- No context was found with the referenced context `name`\n'
                            '- No user was found with the referenced `username`\n'
                            '- User with the referenced `username` is not assigned to context with the referenced '
                            'context `name`\n'
                            '- No context participation API token was found with the given `uuid`, for the '
                            'participation of the user referenced with `username`, to the context referenced with '
                            '`name`'
            )
        }
    )
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

    @extend_schema(
        summary='Revoke context participation API token',
        description='Revoke API token referenced by the `uuid` path parameter and authenticating the '
                    'participation of the user referenced by the `username` path parameter, to the context referenced '
                    'by the `name` path parameter',
        tags=['Context participation tokens'],
        parameters=[
            OpenApiParameter('name', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Name of an existing context', required=True,
                             allow_blank=False, many=False, pattern=settings.CONTEXT_NAME_SLUG_PATTERN),
            OpenApiParameter('username', OpenApiTypes.STR, OpenApiParameter.PATH,
                             description='Username of an existing user', required=True,
                             allow_blank=False, many=False, pattern=settings.USERNAME_SLUG_PATTERN),
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of an issued context participation API token', required=True,
                             allow_blank=False, many=False)
        ],
        responses={
            204: OpenApiResponse(
                description='Context participation API token successfully revoked'
            ),
            400: OpenApiResponse(
                description='Bad request - potentially invalid path parameters'
            ),
            404: OpenApiResponse(
                description='Potential causes:\n'
                            '- No context was found with the referenced context `name`\n'
                            '- No user was found with the referenced `username`\n'
                            '- User with the referenced `username` is not assigned to context with the referenced '
                            'context `name`\n'
                            '- No context participation API token was found with the given `uuid`, for the '
                            'participation of the user referenced with `username`, to the context referenced with '
                            '`name`'
            )
        }
    )
    def delete(self, request, name, username, uuid):
        application_service = request.user

        context_service = ContextService(application_service)
        context = context_service.get_context(name=name)

        auth_entity_service = AuthEntityService(application_service)
        user = auth_entity_service.get_user(username=username)

        api_token_service = ApiTokenService(user, context=context)
        api_token_service.revoke_token(token_uuid=uuid)

        return Response(status=status.HTTP_204_NO_CONTENT)
