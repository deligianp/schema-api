import logging

from django.conf import settings
from django_filters import rest_framework as filters
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter, inline_serializer
from rest_framework import status, serializers
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.constants import _TaskStatus
from api.filtersets import TaskFilter
from api.models import Task
from api.serializers import TaskSerializer, TasksListQPSerializer, TasksBasicListSerializer, \
    TasksDetailedListSerializer, TasksFullListSerializer
from api.services import TaskService
from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsUser, IsActive, IsContextMember
from api_auth.serializers import ContextDetailsSerializer
from quotas.serializers import QuotasSerializer
from quotas.services import QuotasService
from util.paginators import ApplicationPagination

logger = logging.getLogger(__name__)


class ApplicationApiTokenScheme(OpenApiAuthenticationExtension):
    target_class = 'api_auth.auth.ApiTokenAuthentication'
    name = 'API token'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description':
                f'Token-based authentication with required prefix `{settings.AUTHORIZATION_HEADER_PREFIX} `.\n\ne.g. '
                f'For API token of `abcdef1234567890`, value must be `{settings.AUTHORIZATION_HEADER_PREFIX} '
                f'abcdef1234567890`.'
        }


class UserQuotasAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Get applied quotas for user in project',
        description='Get quotas for a user in a project, applied by the corresponding application service',
        tags=['Task'],
        responses={
            200: OpenApiResponse(
                description='Applied quotas for context and participation',
                response=inline_serializer(
                    name='UserQuotasSerializer',
                    fields={
                        'context': QuotasSerializer(),
                        'participation': QuotasSerializer()
                    }
                )
            ),
            400: OpenApiResponse(
                description='Request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            )
        }
    )
    def get(self, request):
        context = request.context
        user = request.user

        quotas_service = QuotasService(context, user=user)
        context_quotas, participation_quotas = quotas_service.get_qualified_quotas()

        data = {
            'context': QuotasSerializer(context_quotas).data,
            'participation': QuotasSerializer(participation_quotas).data
        }

        return Response(status=status.HTTP_200_OK, data=data)


# Temporary endpoint - expected to be removed in the future
class UserContextInfoAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Get context info based on provided API key',
        description='Get details for the context related to the provided API key',
        tags=['Contexts'],
        responses={
            200: OpenApiResponse(
                description='Context info returned',
                response=inline_serializer(
                    name='ContextInfoSerializer',
                    fields={
                        'name': serializers.CharField(),
                        **ContextDetailsSerializer().fields
                    },
                )
            )
        }
    )
    def get(self, request):
        context = request.context
        context_details_serializer = ContextDetailsSerializer(context)
        final_data = context_details_serializer.data
        final_data['name'] = context.name
        return Response(status=status.HTTP_200_OK, data=final_data)


class TasksListCreateAPIView(ListCreateAPIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []
    pagination_class = ApplicationPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = TaskFilter

    def get_queryset(self):
        task_service = TaskService(context=self.request.context) if settings.USE_AUTH else TaskService()
        return task_service.get_tasks()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            task_query_params_serializer = TasksListQPSerializer(data=self.request.query_params.dict())
            task_query_params_serializer.is_valid(raise_exception=True)
            query_params = task_query_params_serializer.validated_data

            if query_params['view'] == 'basic':
                return TasksBasicListSerializer
            elif query_params['view'] == 'detailed':
                return TasksDetailedListSerializer
            else:
                return TasksFullListSerializer
        return TaskSerializer

    @extend_schema(
        summary='List submitted tasks',
        description='List all tasks that have been submitted',
        tags=['Task'],
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Name or UUID part to filter tasks on', required=False,
                             allow_blank=False, many=False, ),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Status to filter tasks on', required=False,
                             allow_blank=False, many=False, enum=[x.label for x in _TaskStatus]),
            OpenApiParameter('before', OpenApiTypes.DATETIME, OpenApiParameter.QUERY,
                             description='Retrieve tasks submitted before this date', required=False,
                             allow_blank=False, many=False),
            OpenApiParameter('after', OpenApiTypes.DATETIME, OpenApiParameter.QUERY,
                             description='Retrieve tasks submitted after this date', required=False,
                             allow_blank=False, many=False),
            OpenApiParameter('order', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Retrieve tasks submitted before this date', required=False,
                             allow_blank=False, many=False,
                             enum=['uuid', '-uuid', 'status', '-status', 'submitted_at', '-submitted_at'])

        ],
        responses={
            200: OpenApiResponse(
                description='For each submitted task, its UUID, its name and submitted timestamp is returned',
                response=TasksFullListSerializer(many=True),
                examples=[
                    OpenApiExample(
                        'valid-list-tasks-output-0',
                        summary='List of submitted tasks',
                        value={
                            "uuid": "bc5f42b2-be41-4dcb-bb31-751dbf5adca1",
                            "name": "hello world",
                            "submitted_at": "2023-03-06T11:38:19.054466Z"
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Task request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super(TasksListCreateAPIView, self).get(request, *args, **kwargs)

    @extend_schema(
        summary='Submit a task execution request.',
        description='Creates a new task request for execution.',
        tags=['Task'],
        request=TaskSerializer,
        examples=[
            OpenApiExample(
                'valid-task-input-0',
                summary='Valid: minimal example',
                description='A task request that defines the minimum required information for it to be valid. The '
                            'task creates a container, based on the ubuntu:latest docker image and runs the command '
                            '`echo hello_world` that prints in standard output the message `hello_world`',
                value={
                    'name': 'hello world',
                    'executors': [
                        {
                            'command': ['echo', 'hello_world'],
                            'image': 'ubuntu:latest'
                        }
                    ]
                },
                request_only=True,
                response_only=False
            ),

            OpenApiExample(
                'valid-task-input-1',
                summary='Valid: complete example',
                description='An example of a task request that provides additional definitions regarding input and output '
                            'files. The task echoes to the standard output the number of lines that an input file has. The '
                            'input file is passed as an input to the container as shown in the `inputs` definition . The '
                            'standard output and standard error streams are being piped to files within the `/data/output` '
                            'directory, which in turn is pulled as output directory, as described in the `outputs` '
                            'definition',
                value={
                    "name": "line counter",
                    "description": "Complete example",
                    "executors": [
                        {
                            "command": [
                                "wc",
                                "-l",
                                "/data/input/file.txt"
                            ],
                            "image": "ubuntu:latest",
                            "stdout": "/data/output/stdout",
                            "stderr": "/data/output/stderr",
                            "workdir": "/home"
                        }
                    ],
                    "inputs": [
                        {
                            "url": "/host/path/input_file.txt",
                            "path": "/data/input/file.txt"
                        }
                    ],
                    "outputs": [
                        {
                            "url": "/host/path/test_output_directory",
                            "path": "/data/output",
                            "type": "DIRECTORY"
                        }
                    ]
                },
                request_only=True,
                response_only=False
            )
        ],
        responses={
            201: OpenApiResponse(
                description='Task request was accepted. Response will contain task information that were provided '
                            'during the request, plus additional information given by **Schema API**.',
                response=TaskSerializer,
                examples=[
                    OpenApiExample(
                        'valid-task-output-0',
                        summary='Submitted task details - SCHEDULED',
                        description='Task was created and was immediately scheduled for execution.',
                        value={
                            "context": "test.context1",
                            "uuid": "90cd67f2-eb3c-485a-a93f-0e99a573ded0",
                            "name": "task1.0",
                            "description": "test_task_description",
                            "status": "SCHEDULED",
                            "submitted_at": "2023-03-03T06:58:54.426118Z",
                            "executors": [
                                {
                                    "image": "ubuntu:20.04",
                                    "command": [
                                        "echo",
                                        "task2"
                                    ]
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'valid-task-output-1',
                        summary='Submitted task details - SUBMITTED',
                        description='Task was successfully created - currently awaiting for scheduling of execution.',
                        value={
                            "context": "test.context1",
                            "uuid": "528d641d-e4ce-4c5b-8b69-aa6d42cf5d16",
                            "name": "hello world",
                            "description": "Complete example",
                            "status": "SUBMITTED",
                            "submitted_at": "2023-03-06T14:02:52.146207Z",
                            "executors": [
                                {
                                    "image": "ubuntu:latest",
                                    "command": [
                                        "wc",
                                        "-l",
                                        "/data/input/file.txt"
                                    ],
                                    "stdout": "/data/output/stdout",
                                    "stderr": "/data/output/stderr",
                                    "workdir": "/home",
                                }
                            ],
                            "inputs": [
                                {
                                    "url": "/host/path/input_file.txt",
                                    "path": "/data/input/file.txt",
                                    "type": "FILE"
                                }
                            ],
                            "outputs": [
                                {
                                    "url": "/host/path/test_output_directory",
                                    "path": "/data/output",
                                    "type": "DIRECTORY"
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Task request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            )
        }
    )
    def post(self, request, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_service = TaskService(context=request.context,
                                   auth_entity=request.user) if settings.USE_AUTH else TaskService()
        task = task_service.submit_task(**serializer.validated_data)
        stored_data = TaskSerializer(task).data
        return Response(status=status.HTTP_201_CREATED, data=stored_data)


class TaskRetrieveAPIView(RetrieveAPIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []
    lookup_field = 'uuid'
    serializer_class = TaskSerializer

    @extend_schema(
        summary='Get task\'s details',
        description='Retrieve details for a particular task, identified by its assigned UUID',
        tags=['Task'],
        parameters=[
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of the target task that was assigned during submission', required=True,
                             allow_blank=False, many=False, )
        ],
        responses={
            200: OpenApiResponse(
                description='Details of the task specified by the UUID are returned',
                response=TaskSerializer,
                examples=[
                    OpenApiExample(
                        'valid-task-output-0',
                        summary='Details of a currently running task',
                        value={
                            "context": "test.context1",
                            "uuid": "90cd67f2-eb3c-485a-a93f-0e99a573ded0",
                            "name": "task1.0",
                            "description": "test_task_description",
                            "status_history": [
                                {
                                    "status": "SUBMITTED",
                                    "updated_at": "2024-01-01T00:00:00.000000Z"
                                },
                                {
                                    "status": "APPROVED",
                                    "updated_at": "2024-01-01T00:00:01.000000Z"
                                },
                                {
                                    "status": "SCHEDULED",
                                    "updated_at": "2024-01-01T00:00:02.000000Z"
                                },
                                {
                                    "status": "RUNNING",
                                    "updated_at": "2024-01-01T00:00:03.000000Z"
                                }
                            ],
                            "submitted_at": "2023-03-03T06:58:54.426118Z",
                            "executors": [
                                {
                                    "image": "ubuntu:20.04",
                                    "command": [
                                        "echo",
                                        "task2"
                                    ]
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'valid-task-output-1',
                        summary='Details of a task that unfortunately ended with an error',
                        value={
                            "context": "test.context1",
                            "uuid": "90cd67f2-eb3c-485a-a93f-0e99a573ded0",
                            "name": "task1.0",
                            "description": "test_task_description",
                            "status_history": [
                                {
                                    "status": "SUBMITTED",
                                    "updated_at": "2024-01-01T00:00:00.000000Z"
                                },
                                {
                                    "status": "APPROVED",
                                    "updated_at": "2024-01-01T00:00:01.000000Z"
                                },
                                {
                                    "status": "SCHEDULED",
                                    "updated_at": "2024-01-01T00:00:02.000000Z"
                                },
                                {
                                    "status": "ERROR",
                                    "updated_at": "2024-01-01T00:00:03.000000Z"
                                }
                            ],
                            "submitted_at": "2023-03-03T06:58:54.426118Z",
                            "executors": [
                                {
                                    "image": "ubuntu:20.04",
                                    "command": [
                                        "echo",
                                        "task2"
                                    ]
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'valid-task-output-2',
                        summary='Details of a successfully completed task',
                        value={
                            "context": "test.context1",
                            "uuid": "528d641d-e4ce-4c5b-8b69-aa6d42cf5d16",
                            "name": "hello world",
                            "description": "Complete example",
                            "status_history": [
                                {
                                    "status": "SUBMITTED",
                                    "updated_at": "2024-01-01T00:00:00.000000Z"
                                },
                                {
                                    "status": "APPROVED",
                                    "updated_at": "2024-01-01T00:00:01.000000Z"
                                },
                                {
                                    "status": "SCHEDULED",
                                    "updated_at": "2024-01-01T00:00:02.000000Z"
                                },
                                {
                                    "status": "COMPLETED",
                                    "updated_at": "2024-01-01T00:00:03.000000Z"
                                }
                            ],
                            "submitted_at": "2023-03-06T14:02:52.146207Z",
                            "executors": [
                                {
                                    "image": "ubuntu:latest",
                                    "command": [
                                        "wc",
                                        "-l",
                                        "/data/input/file.txt"
                                    ],
                                    "stdout": "/data/output/stdout",
                                    "stderr": "/data/output/stderr",
                                    "workdir": "/home",
                                }
                            ],
                            "inputs": [
                                {
                                    "url": "/host/path/input_file.txt",
                                    "path": "/data/input/file.txt",
                                    "type": "FILE"
                                }
                            ],
                            "outputs": [
                                {
                                    "url": "/host/path/test_output_directory",
                                    "path": "/data/output",
                                    "type": "DIRECTORY"
                                }
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Task request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            ),
            404: OpenApiResponse(
                description='Given UUID does not match an existing task'
            )
        }
    )
    def get(self, request, uuid, **kwargs):
        task_service = TaskService(context=request.context) if settings.USE_AUTH else TaskService()
        try:
            task = task_service.get_task(uuid)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'No task was found with UUID "{uuid}"'})
        task_serializer = self.serializer_class(task)
        return Response(status=status.HTTP_200_OK, data=task_serializer.data)


class TaskStdoutAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Get task\'s standard output',
        description='Retrieve task\'s standard output, for each executor, as long as it hasn\'t been piped to a file '
                    'and as long as the executor has already produced it.',
        tags=['Task'],
        parameters=[
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of the target task that was assigned during submission', required=True,
                             allow_blank=False, many=False, )
        ],
        responses={
            200: OpenApiResponse(
                description='Stdout of the task specified by the UUID are returned',
                response=TaskSerializer,
                examples=[
                    OpenApiExample(
                        'valid-task-stdout-0',
                        summary='Stdout of a task with a single executor that sorts a list of numbers',
                        value={
                            "stdout": ["Sorting: [5,1,3,2,4,6]\nResult:[1,2,4,5,6]"]
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'valid-task-stdout-1',
                        summary='Stdout of a task with multiple executors: one that sort a list of numbers and one '
                                'that given a list keeps only the prime numbers',
                        value={
                            "stdout": [
                                "Sorting: [5,1,3,2,4,6]\nResult:[1,2,4,5,6]",
                                "primes from input 1,2,3,4,5 are:\n    1,2,3,5"
                            ]
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            ),
            404: OpenApiResponse(
                description='Given UUID does not match an existing task'
            )
        }
    )
    def get(self, request, uuid):
        task_service = TaskService(context=request.context) if settings.USE_AUTH else TaskService()
        try:
            task_stdout = task_service.get_task_stdout(uuid)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'No task was found with UUID "{uuid}"'})
        return Response(status=status.HTTP_200_OK, data={'stdout': task_stdout})


class TaskStderrAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Get task\'s standard error stream',
        description='Retrieve task\'s standard error stream, for each executor, as long as it hasn\'t been piped to a '
                    'file and as long as the executor has already produced it.',
        tags=['Task'],
        parameters=[
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of the target task that was assigned during submission', required=True,
                             allow_blank=False, many=False, )
        ],
        responses={
            200: OpenApiResponse(
                description='Stderr of the task specified by the UUID are returned',
                response=TaskSerializer,
                examples=[
                    OpenApiExample(
                        'valid-task-stderr-0',
                        summary='Stderr of a task that raised an error',
                        value={
                            "stderr": ["ValueError: Value 'abcde' is not an integer"]
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            ),
            404: OpenApiResponse(
                description='Given UUID does not match an existing task'
            )
        }
    )
    def get(self, request, uuid):
        task_service = TaskService(context=request.context) if settings.USE_AUTH else TaskService()
        try:
            task_stderr = task_service.get_task_stderr(uuid)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'No task was found with UUID "{uuid}"'})
        return Response(status=status.HTTP_200_OK, data={'stderr': task_stderr})


class TaskCancelAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Cancel a task',
        description='Cancel a task, if it\'s still running.',
        tags=['Task'],
        parameters=[
            OpenApiParameter('uuid', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='UUID of the target task that was assigned during submission', required=True,
                             allow_blank=False, many=False, )
        ],
        responses={
            202: OpenApiResponse(
                description='Task was cancelled',
            ),
            400: OpenApiResponse(
                description='Request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. Perhaps no API token was provided in the `Authorization` header, '
                            'or the API token was invalid.'
            ),
            404: OpenApiResponse(
                description='Given UUID does not match an existing task'
            )
        }
    )
    def post(self, request, uuid):
        task_service = TaskService(context=request.context,
                                   auth_entity=request.user) if settings.USE_AUTH else TaskService()
        task_service.cancel_task(uuid)
        return Response(status=status.HTTP_202_ACCEPTED)
