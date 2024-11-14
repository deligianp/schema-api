from django.conf import settings
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

    def get(self, request):
        experiment_service = ExperimentService(request.context)
        experiments = experiment_service.list_experiments()

        output_serializer = ExperimentsListSerializer(experiments, many=True)
        return Response(status=status.HTTP_200_OK, data=output_serializer.data)

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

    def get(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.retrieve_experiment(name, creator)

        output_serializer = ExperimentSerializer(experiment)
        return Response(status=status.HTTP_200_OK, data=output_serializer.data)

    def patch(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        input_serializer = ExperimentUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.update_experiment(creator, name, **input_serializer.validated_data)

        output_serializer = ExperimentSerializer(experiment)
        return Response(status=status.HTTP_202_ACCEPTED, data=output_serializer.data)

    def delete(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        experiment_service = ExperimentService(request.context)
        experiment_service.delete_experiment(name, creator)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ExperimentTasksAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive, IsContextMember] if settings.USE_AUTH else []

    def put(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        if not request.data:
            raise ApplicationValidationError('No task UUIDs were provided in request body')

        task_uuids = set(request.data)
        task_service = TaskService(context=request.context)

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

    def get(self, request, username: str, name: str):
        auth_entity_service = AuthEntityService(request.user.parent)
        creator = auth_entity_service.get_user(username)

        experiment_service = ExperimentService(request.context)
        experiment = experiment_service.retrieve_experiment(name, creator)

        experiment_task_service = ExperimentTaskService(experiment)

        tasks = experiment_task_service.get_tasks()
        output_serializer = TasksBasicListSerializer(tasks, many=True)
        return Response(status=status.HTTP_200_OK, data=output_serializer.data)
