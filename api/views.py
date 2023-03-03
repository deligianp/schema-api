# Create your views here.
from django.conf import settings
from knox.auth import TokenAuthentication
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import Task
from api.serializers import TaskSerializer
from api.services import TaskService
from api_auth.permissions import IsContext
from schema_api.settings import USE_AUTH


class TaskViewSet(viewsets.ViewSet):
    lookup_field = 'uuid'
    authentication_classes = [TokenAuthentication] if USE_AUTH else []
    permission_classes = [IsAuthenticated, IsContext] if USE_AUTH else []

    class ListTaskSerialzier(TaskSerializer):
        def get_fields(self):
            fields = super().get_fields()
            return {key: fields[key] for key in ['uuid', 'name', 'submitted_at'] if key in fields}

    def retrieve(self, request, uuid=None):
        task_service = TaskService(context=request.user) if settings.USE_AUTH else TaskService()
        try:
            task = task_service.get_task(uuid)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'No task was found with UUID "{uuid}"'})
        task_serializer = TaskSerializer(task)
        return Response(status=status.HTTP_200_OK, data=task_serializer.data)

    def list(self, request):
        task_service = TaskService(context=request.user) if settings.USE_AUTH else TaskService()
        tasks = task_service.get_tasks()
        task_serializer = self.ListTaskSerialzier(tasks, many=True)
        return Response(status=status.HTTP_200_OK, data=task_serializer.data)

    def create(self, request):
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_service = TaskService(context=request.user) if settings.USE_AUTH else TaskService()
        task = task_service.submit_task(**serializer.validated_data)

        stored_data = TaskSerializer(task).data


            task_service = TaskService(**task_info)
            try:
                task = task_service.save()
            except DjangoValidationError as d_ve:
                raise DRFValidationError(d_ve.message_dict)
            task_uuid = task.uuid
            return Response(status=status.HTTP_201_CREATED, data={'uuid': task_uuid})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
