import abc
import json
from abc import ABC
from urllib.parse import urljoin

import requests
from rest_framework import status

from api.constants import TaskStatus
from api.models import Task
from api.serializers import TesTaskSerializer, TesExecutorSerializer, TesMountPointSerializer
from schema_api import settings


class AbstractTaskApi(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def create_task(self, task: Task = None, executors_configurations=None, mount_points=None, volumes=None, tags=None):
        pass

    @abc.abstractmethod
    def get_task_by_id(self, task_id=None, task_api_get_endpoint=None):
        pass


class BaseTaskApi(AbstractTaskApi, ABC):

    def __init__(self, *args, **kwargs):
        try:
            self.name = self.Meta.name
        except AttributeError as ae:
            ae.args = ('\n'.join((
                *ae.args,
                'Name of the task execution runtime configuration in application settings must be'
                ' defined in TaskApi\'s inner Meta class, in "name" attribute'
            )),)
            raise ae.with_traceback(ae.__traceback__)
        self.post_endpoint = settings.TASK_APIS.get(self.name)['TASK_POST_ENDPOINT']
        self.get_endpoint = settings.TASK_APIS.get(self.name)['TASK_GET_ENDPOINT']
        self.protocol = settings.TASK_APIS.get(self.name)['PROTOCOL']

    class Meta:
        pass


class TesRuntime(BaseTaskApi):
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

    class Meta:
        name = 'TES'

    def get_task_by_id(self, task_id=None, task_api_get_endpoint=None):
        if task_api_get_endpoint is None:
            task_api_get_endpoint = self.get_endpoint
        # qualified_url = urljoin(task_api_get_endpoint, task_id)
        qualified_url = f'{task_api_get_endpoint}/{task_id}?view=FULL'
        r = requests.get(url=qualified_url)
        if r.status_code == status.HTTP_200_OK:
            response_content = json.loads(r.content)
            return self.TES_SCHEMA_STATUS_MAP[response_content['state']]
        else:
            if str(r.status_code)[0] == '4':
                # log that request sent from schema-api was invalid
                # potential error that must be fixed in schema-api
                pass
            raise RuntimeError('An error occurred when posting task to TES runtime')

    def create_task(self, task: Task = None, executors_configurations=None, mount_points=None, volumes=None, tags=None):
        task_data = TesTaskSerializer(task).data

        executors_data = list()
        for executor_configuration in executors_configurations:
            executor = executor_configuration['executor']
            envs = executor_configuration.get('envs', None)
            executor_data = TesExecutorSerializer(executor).data
            if envs is not None:
                envs_data = {env.key: env.value for env in envs}
                executor_data['env'] = envs_data
            executors_data.append(executor_data)
        task_data['executors'] = executors_data

        if mount_points is not None:
            inputs_data = list()
            outputs_data = list()
            for mount_point in mount_points:
                mount_point_data = TesMountPointSerializer(mount_point, protocol=self.protocol).data
                inputs_data.append(mount_point_data) if mount_point.is_input else outputs_data.append(mount_point_data)
            task_data['inputs'] = inputs_data
            task_data['outputs'] = outputs_data

        if volumes is not None:
            volumes_data = [volume.path for volume in volumes]
            task_data['volumes'] = volumes_data

        if tags is not None:
            tags_data = {tag.key: tag.value for tag in tags}
            task_data['tags'] = tags_data

        r = requests.post(
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            url=self.post_endpoint,
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
