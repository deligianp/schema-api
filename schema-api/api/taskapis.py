import abc
import importlib
import json
from abc import ABC
from urllib.parse import urljoin

import requests
from rest_framework import status

from api.constants import TaskStatus
from api.models import Task
from api.serializers import TaskSerializer
from django.conf import settings


class AbstractTaskApi(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def create_task(self, task: Task):
        pass

    @abc.abstractmethod
    def get_task_info(self, task_id):
        pass

    @abc.abstractmethod
    def get_task_status(self, task_id):
        pass

    @abc.abstractmethod
    def get_tasks(self):
        pass

    @abc.abstractmethod
    def get_executor_logs(self, task_id, executor_index):
        pass


class BaseTaskApi(AbstractTaskApi, ABC):

    def __init__(self, *args, **kwargs):
        self.post_task_endpoint = settings.TASK_API['CREATE_TASK_ENDPOINT']
        self.get_task_endpoint = settings.TASK_API['GET_TASK_ENDPOINT']
        # self.protocol = settings.TASK_API['PROTOCOL']


class TesTaskApi(BaseTaskApi):
    class PostTaskSerializer(TaskSerializer):
        pass

    def get_tasks(self):
        return []

    def get_task_info(self, task_id):
        task_content = self._get_task(task_id)
        result = self.get_executor_logs(task_id, task_content=task_content)
        result['status'] = self.get_task_status(task_id, task_content=task_content)
        return result

    def get_task_status(self, task_id, task_content=None):
        if not task_content:
            task_content = self._get_task(task_id)
        return self.TES_SCHEMA_STATUS_MAP[task_content['state']]

    def get_executor_logs(self, task_id, executor_index: int = None, task_content=None):
        result = {}
        if not task_content:
            task_content = self._get_task(task_id)
        tasks_logs = task_content.get('logs', None)

        # Deeply nested code is following - shameful display
        if tasks_logs and len(tasks_logs) > 0:
            task_logs = tasks_logs[0]
            executors_logs = task_logs.get('logs', None)
            if executors_logs and len(executors_logs) > 0:
                if executor_index and len(executors_logs) > executor_index:
                    executor_logs = executors_logs[executor_index]
                    result['stdout'] = executor_logs.get('stdout', '')
                    result['stderr'] = executor_logs.get('stderr', '')
                elif not executor_index:
                    result['stderr'] = []
                    result['stdout'] = []
                    for executor_logs in executors_logs:
                        result['stderr'].append(executor_logs.get('stderr', ''))
                        result['stdout'].append(executor_logs.get('stdout', ''))
        return result

    TES_SCHEMA_STATUS_MAP = {
        'UNKNOWN': TaskStatus.UNKNOWN,
        'INITIALIZING': TaskStatus.INITIALIZING,
        'QUEUED': TaskStatus.INITIALIZING,
        'RUNNING': TaskStatus.RUNNING,
        'PAUSED': TaskStatus.RUNNING,
        'COMPLETE': TaskStatus.COMPLETED,
        'EXECUTOR_ERROR': TaskStatus.ERROR,
        'SYSTEM_ERROR': TaskStatus.ERROR,
        'CANCELED': TaskStatus.CANCELED
    }

    def _get_task(self, task_id):
        qualified_url = f'{urljoin(self.get_task_endpoint, task_id)}?view=FULL'
        r = requests.get(url=qualified_url)
        if r.status_code == status.HTTP_200_OK:
            response_content = json.loads(r.content)
            return response_content
        else:
            if str(r.status_code)[0] == '4':
                # log that request sent from schema-api was invalid
                # potential error that must be fixed in schema-api
                pass
            raise RuntimeError('An error occurred when retrieving task from TES runtime')

    def create_task(self, task):
        task_data = self.PostTaskSerializer(task).data

        # Remove fields that do not exist in TES
        task_data.pop('uuid', None)
        task_data.pop('submitted_at', None)
        task_data.pop('status', None)

        related_context = task_data.pop('context', '')
        if related_context:
            task_data['name'] = related_context + '.' + task_data['name']

        r = requests.post(
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            url=self.post_task_endpoint,
            data=json.dumps(task_data)
        )
        if r.status_code == status.HTTP_200_OK:
            response_content = json.loads(r.content)
            return response_content['id']
        else:
            if str(r.status_code)[0] == '4':
                # log that request sent from schema-api was
                pass
            raise RuntimeError('An error occurred when posting task to TES runtime')


def get_task_api_class():
    if settings.TASK_API:
        task_api_class_module, task_api_class_name = settings.TASK_API.get('TASK_API_CLASS').rsplit('.', 1)
        module = importlib.import_module(task_api_class_module)
        task_api_class = getattr(module, task_api_class_name)
        return task_api_class
