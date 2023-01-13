# Create your views here.
from django.core.exceptions import ValidationError as DjangoValidationError
from knox.auth import TokenAuthentication
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import Task
from api.serializers import TaskSerializer
from api.services import TaskService
from api_auth.permissions import IsContext
from schema_api.settings import USE_AUTH


class TaskViewSet(viewsets.ViewSet):
    class OutputSimpleSerializer(TaskSerializer):
        class Meta:
            fields = ['uuid', 'status']

    lookup_field = 'uuid'
    authentication_classes = [TokenAuthentication] if USE_AUTH else []
    permission_classes = [IsAuthenticated, IsContext] if USE_AUTH else []

    def retrieve(self, request, uuid=None):
        try:
            task = TaskService.get_status(uuid)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'No task was found with UUID "{uuid}"'})
        task_serializer = TaskSerializer(task)
        return Response(status=status.HTTP_200_OK, data=task_serializer.data)

    def list(self, request):
        tasks = Task.objects.all()
        serializer = self.OutputSimpleSerializer(tasks, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = TaskSerializer(data=request.data)
        # data = request.data
        if serializer.is_valid():
            task_info = serializer.create(serializer.validated_data)
            task_service = TaskService(**task_info)
            try:
                task = task_service.save()
            except DjangoValidationError as d_ve:
                raise DRFValidationError(d_ve.message_dict)
            task_uuid = task.uuid
            return Response(status=status.HTTP_201_CREATED, data={'uuid': task_uuid})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
