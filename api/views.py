# Create your views here.
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from knox.auth import TokenAuthentication
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.constants import TaskStatus
from api.models import Task
from api.serializers import TaskSerializer
from api.services import TaskService, TaskStatsService
from api_auth.permissions import IsContext
from api_auth.services import ContextService
from schema_api.settings import USE_AUTH


class TaskViewSet(viewsets.ViewSet):
    class OutputSimpleSerializer(TaskSerializer):
        class Meta:
            fields = ['uuid']

    lookup_field = 'uuid'
    authentication_classes = [TokenAuthentication] if USE_AUTH else []
    permission_classes = [IsAuthenticated, IsContext] if USE_AUTH else []

    def retrieve(self, request, uuid=None):
        try:
            if settings.USE_AUTH:
                task = TaskService.get_status(uuid, context=request.user)
            else:
                task = TaskService.get_status(uuid)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'No task was found with UUID "{uuid}"'})
        task_serializer = TaskSerializer(task)
        return Response(status=status.HTTP_200_OK, data=task_serializer.data)

    def list(self, request):
        if settings.USE_AUTH:
            task_set = Task.objects.filter(context=request.user)
        else:
            task_set = Task.objects.all()
        acceptable_status = TaskStatus.values + (['CHARGED'] if settings.USE_AUTH else [])
        task_status = request.query_params.get('status', None)
        if task_status:
            task_status = task_status.upper()
            if task_status not in acceptable_status:
                raise DRFValidationError(
                    'Query parameter "status" must have one of the following values: ' + ', '.join(acceptable_status))
            if task_status == 'CHARGED':
                tasks = ContextService.get_charged_tasks(request.user)
            else:
                tasks = task_set.filter(status=TaskStatus(task_status))
        else:
            tasks = task_set

        data = [{'uuid': task.uuid} for task in tasks]
        return Response(data)

    def create(self, request):
        serializer = TaskSerializer(data=request.data)
        # data = request.data
        if serializer.is_valid():
            task_info = serializer.create(serializer.validated_data)
            if USE_AUTH:
                task_info['task'].context = request.user

                # check whether more jobs can be executed


            task_service = TaskService(**task_info)
            try:
                task = task_service.save()
            except DjangoValidationError as d_ve:
                raise DRFValidationError(d_ve.message_dict)
            task_uuid = task.uuid
            return Response(status=status.HTTP_201_CREATED, data={'uuid': task_uuid})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
