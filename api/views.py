import random

# Create your views here.
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from api.models import Task
from api.taskapis import TesRuntime
from api.serializers import TaskSerializer
from api.services import TaskService


class TaskViewSet(viewsets.ViewSet):
    class OutputSimpleSerializer(TaskSerializer):
        class Meta:
            fields = ['uuid', 'status']

    lookup_field = 'uuid'

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


def get_api_response():
    id_int = random.randint(0, 4294967295)
    task_id = f'task-{hex(id_int)[2:]}'
    return {
        "tesk_id": task_id,
    }
