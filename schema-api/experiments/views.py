from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import TasksBasicListSerializer
from api.services import TaskService
from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsUser, IsActive, IsContextMember
from api_auth.services import AuthEntityService
from experiments.serializers import ExperimentsListSerializer, ExperimentSerializer, ExperimentUpdateSerializer
from experiments.services import ExperimentService, ExperimentTaskService
from util.exceptions import ApplicationValidationError, ApplicationNotFoundError


# Create your views here.
class ExperimentsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='List experiments',
        description='Retrieve a list of all experiments created in the corresponding execution context.',
        tags=['Experiments'],
        responses={
            200: OpenApiResponse(
                description='Returns a list of experiments related to the corresponding execution context.',
                response=ExperimentsListSerializer,
                examples=[
                    OpenApiExample(
                        'empty-list',
                        summary='No experiments exist',
                        value=[],
                        request_only=False,
                        response_only=True
                    ),
                    OpenApiExample(
                        'list-of-experiments',
                        summary='List of experiments',
                        value=[
                            {
                                "name": "experiment0",
                                "created_at": "2024-01-01T06:24:43.008062Z",
                                "creator": "Kylie"
                            },
                            {
                                "name": "experiment1",
                                "created_at": "2024-01-01T06:24:49.818868Z",
                                "creator": "Kylie"
                            }
                        ],
                        request_only=False,
                        response_only=True
                    )
                ]
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            )
        }
    )
    def get(self, request):
        experiment_service = ExperimentService(request.context)
        experiments = experiment_service.list_experiments()

        output_serializer = ExperimentsListSerializer(experiments, many=True)
        return Response(status=status.HTTP_200_OK, data=output_serializer.data)

    @extend_schema(
        summary='Create an experiment',
        description='Create a new experiment with the specified name and optional description.',
        tags=['Experiments'],
        request=ExperimentSerializer,
        examples=[
            OpenApiExample(
                'minimal-example',
                summary='Minimal example',
                value={
                    'name': 'experiment'
                },
                request_only=True,
                response_only=False,
            ),
            OpenApiExample(
                'example-with-description',
                summary='Example with description',
                value={
                    'name': 'experiment',
                    'description': 'Example with description'
                },
                request_only=True,
                response_only=False,
            )
        ],
        responses={
            201: OpenApiResponse(
                description='New experiment was created.',
                response=ExperimentSerializer,
                examples=[
                    OpenApiExample(
                        'experiment-created-with-empty-description',
                        summary='Experiment created with empty description',
                        value={
                            "name": "experiment",
                            "description": "",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'experiment-created-with-description',
                        summary='Experiment created with description',
                        value={
                            "name": "experiment",
                            "description": "Some description about the experiment",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid experiment data'
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            ),
            409: OpenApiResponse(
                description='Experiment name is used by another experiment'
            )
        }
    )
    def post(self, request):
        input_serializer = ExperimentSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.create_experiment(creator=request.user, **input_serializer.validated_data)

        output_serializer = ExperimentSerializer(experiment)

        return Response(status=status.HTTP_201_CREATED, data=output_serializer.data)


class ExperimentDetailsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Retrieve an experiment',
        description='Retrieve details of a specific experiment by creator and experiment name.',
        tags=['Experiments'],
        responses={
            201: OpenApiResponse(
                description='Experiment was found and retrieved.',
                response=ExperimentSerializer,
                examples=[
                    OpenApiExample(
                        'experiment-retrieved-with-empty-description',
                        summary='Experiment retrieved with empty description',
                        value={
                            "name": "experiment",
                            "description": "",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'experiment-retrieved-with-description',
                        summary='Experiment retrieved with description',
                        value={
                            "name": "experiment",
                            "description": "Some description about the experiment",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid experiment data'
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            ),
            404: OpenApiResponse(
                description='Either user is not a context participant or experiment not found in context'
            )
        }
    )
    def get(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.retrieve_experiment(name, creator)

        output_serializer = ExperimentSerializer(experiment)
        return Response(status=status.HTTP_200_OK, data=output_serializer.data)

    @extend_schema(
        summary='Update an experiment',
        description='Update experiment metadata',
        tags=['Experiments'],
        request=ExperimentUpdateSerializer,
        examples=[
            OpenApiExample(
                'update-only-name',
                summary='Update experiment name',
                value={
                    'name': 'new_name'
                }
            ),
            OpenApiExample(
                'update-only-description',
                summary='Update experiment description',
                value={
                    'description': 'New description'
                }
            ),
            OpenApiExample(
                'update-name-description',
                summary='Update experiment name and description',
                value={
                    'name': 'new_name',
                    'description': 'New description'
                }
            )
        ],
        responses={
            202: OpenApiResponse(
                description='Experiment was found and updated with given data.',
                response=ExperimentSerializer,
                examples=[
                    OpenApiExample(
                        'experiment-updated-with-new-description',
                        summary='Experiment updated with new description',
                        value={
                            "name": "experiment",
                            "description": "New description",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'experiment-updated-with-new-name',
                        summary='Experiment updated with new name',
                        value={
                            "name": "new_name",
                            "description": "",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'experiment-updated-with-new-name-and-description',
                        summary='Experiment updated with new name and description',
                        value={
                            "name": "new_name",
                            "description": "New description",
                            "created_at": "2022-09-27T18:00:00.000",
                            "creator": "user"
                        },
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid experiment data'
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            ),
            404: OpenApiResponse(
                description='Either user is not a context participant or experiment not found in context'
            ),
            409: OpenApiResponse(
                description='Updated experiment name is used by another experiment'
            )
        }
    )
    def patch(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        input_serializer = ExperimentUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.update_experiment(creator, name, **input_serializer.validated_data)

        output_serializer = ExperimentSerializer(experiment)
        return Response(status=status.HTTP_202_ACCEPTED, data=output_serializer.data)

    @extend_schema(
        summary='Delete an experiment',
        description='Delete an experiment',
        tags=['Experiments'],
        responses={
            204: OpenApiResponse(
                description='Experiment was found and deleted.'
            ),
            400: OpenApiResponse(
                description='Invalid experiment data'
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            ),
            404: OpenApiResponse(
                description='Either user is not a context participant or experiment not found in context'
            )
        }
    )
    def delete(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        experiment_service = ExperimentService(request.context)
        experiment_service.delete_experiment(name, creator)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ExperimentTasksAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Set experiment tasks',
        description='Set experiment tasks by task UUID',
        tags=['Experiments'],
        request=True,
        examples=[
            OpenApiExample(
                'set-experiment-no-tasks',
                summary='Set experiment to have no tasks',
                value=[],
                request_only=True,
                response_only=False,
            ),
            OpenApiExample(
                'set-experiment-tasks',
                summary='Set experiment tasks',
                value=[
                    "551ec417-e034-4c3e-811b-69cba5cb377a",
                    "4883e205-274c-4f16-8fb6-b46199d759a5",
                    "6132f1ce-b557-4f43-852d-873252721ae1"
                ],
                request_only=True,
                response_only=False,
            )
        ],
        responses={
            202: OpenApiResponse(
                description='Experiment was found and task list was updated',
                response=TasksBasicListSerializer,
                examples=[
                    OpenApiExample(
                        'updated-experiment-tasks-list',
                        summary='Updated experiment tasks list',
                        value=[
                            {
                                "uuid": "551ec417-e034-4c3e-811b-69cba5cb377a",
                                "name": "foo_task",
                                "state": {
                                    "status": "APPROVED",
                                    "updated_at": "2024-11-13T11:49:06.320683Z"
                                }
                            },
                            {
                                "uuid": "4883e205-274c-4f16-8fb6-b46199d759a5",
                                "name": "foo_task",
                                "state": {
                                    "status": "APPROVED",
                                    "updated_at": "2024-11-14T06:22:40.766514Z"
                                }
                            }
                        ],
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'updated-experiment-tasks-list-with-no-tasks',
                        summary='Updated experiment tasks list with no tasks',
                        value=[],
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid experiment data'
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            ),
            404: OpenApiResponse(
                description='Either user is not a context participant, experiment not found in context or a referenced '
                            'task does not exist in context'
            )
        }
    )
    def put(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        if not request.data:
            raise ApplicationValidationError('No task UUIDs were provided in request body')

        task_uuids = set(request.data)
        task_service = TaskService(context=request.context, auth_entity=creator)

        tasks = task_service.get_tasks().filter(uuid__in=task_uuids)
        if len(task_uuids) != len(tasks):
            indicative_uuid = task_uuids.difference(set(str(t.uuid) for t in tasks)).pop()

            raise ApplicationNotFoundError(f'No task with UUID "{indicative_uuid}" exists in context '
                                           f'"{request.context.name}"')

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.retrieve_experiment(name, creator)

        experiment_task_service = ExperimentTaskService(experiment)
        experiment_task_service.set_tasks(tasks)

        output_serializer = TasksBasicListSerializer(experiment_task_service.get_tasks(), many=True)
        return Response(status=status.HTTP_202_ACCEPTED, data=output_serializer.data)

    @extend_schema(
        summary='Get experiment tasks',
        description='Get experiment tasks',
        tags=['Experiments'],
        responses={
            200: OpenApiResponse(
                description='Experiment was found and task list was updated',
                response=TasksBasicListSerializer,
                examples=[
                    OpenApiExample(
                        'experiment-tasks-list',
                        summary='Experiment tasks list',
                        value=[
                            {
                                "uuid": "551ec417-e034-4c3e-811b-69cba5cb377a",
                                "name": "foo_task",
                                "state": {
                                    "status": "APPROVED",
                                    "updated_at": "2024-11-13T11:49:06.320683Z"
                                }
                            },
                            {
                                "uuid": "4883e205-274c-4f16-8fb6-b46199d759a5",
                                "name": "foo_task",
                                "state": {
                                    "status": "APPROVED",
                                    "updated_at": "2024-11-14T06:22:40.766514Z"
                                }
                            }
                        ],
                        request_only=False,
                        response_only=True,
                    ),
                    OpenApiExample(
                        'Experiment-tasks-list-with-no-tasks',
                        summary='Experiment tasks list with no tasks',
                        value=[],
                        request_only=False,
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid experiment data'
            ),
            401: OpenApiResponse(
                description='Invalid credentials or credentials were not provided.'
            ),
            403: OpenApiResponse(
                description='Insufficient permissions'
            ),
            404: OpenApiResponse(
                description='Either user is not a context participant, experiment not found in context or a referenced '
                            'task does not exist in context'
            )
        }
    )
    def get(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.retrieve_experiment(name, creator)

        experiment_task_service = ExperimentTaskService(experiment)

        tasks = experiment_task_service.get_tasks()
        output_serializer = TasksBasicListSerializer(tasks, many=True)
        return Response(status=status.HTTP_200_OK, data=output_serializer.data)
