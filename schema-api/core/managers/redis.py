import base64
import dataclasses
import json
import uuid
from datetime import datetime
from dateutil import parser
from enum import IntEnum, Enum
from typing import Dict, Optional, List, Tuple

import redis
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from rest_framework import serializers

from api.constants import TaskStatus
from core.managers.base import BaseExecutionManager, ExecutionManifest, UserInfo, LiveExecutionData, ExecutionDetails
from util.exceptions import ApplicationMissingExecutionError
from workflows.constants import WorkflowLanguages


class RedisExecutionStatus(IntEnum):
    QUEUED = 0
    SCHEDULED = 1
    INITIALIZING = 2
    RUNNING = 3
    TERMINATING = 4
    ERROR = 5
    COMPLETED = 6
    CANCELED = 7
    EVICTED = 8


class RedisExecutionEventTypes(Enum):
    STATUS_UPDATED = 'Status updated'
    QUOTAS_UPDATED = 'Quotas updated'


@dataclasses.dataclass
class RedisExecutionEvent:
    type: RedisExecutionEventTypes
    created_at: datetime = dataclasses.field(default_factory=datetime.now)
    details: Dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class RedisExecutionData:
    user_info: UserInfo
    context_id: str
    status: Optional[RedisExecutionStatus] = None
    execution: Optional[ExecutionDetails] = None
    events: Optional[List[RedisExecutionEvent]] = dataclasses.field(default_factory=list)
    quotas: Optional[Dict] = dataclasses.field(default_factory=dict)
    metadata: Optional[Dict] = dataclasses.field(default_factory=dict)
    stdout: Optional[List[str]] = dataclasses.field(default_factory=list)
    stderr: Optional[List[str]] = dataclasses.field(default_factory=list)
    ref_id: str = dataclasses.field(default_factory=lambda: uuid.uuid4().hex)


class RedisExecutionUserInfoSerializer(serializers.Serializer):
    unique_id = serializers.CharField()
    username = serializers.CharField(required=False)
    fs_user_dir = serializers.CharField(required=False)


class RedisExecutionDetailsSerializer(serializers.Serializer):
    definition = serializers.CharField()
    is_task = serializers.BooleanField(default=False)
    language = serializers.ChoiceField(choices=WorkflowLanguages.choices, required=False)
    version = serializers.CharField(required=False)

    def to_representation(self, instance):
        default_representation = super(RedisExecutionDetailsSerializer, self).to_representation(instance)

        default_representation['definition'] = base64.b64encode(
            default_representation['definition'].encode('utf-8')).decode('utf-8')

        return default_representation

    def to_internal_value(self, data):
        default_internal_value = super(RedisExecutionDetailsSerializer, self).to_internal_value(data)

        default_internal_value['definition'] = base64.b64decode(
            default_internal_value['definition'].encode('utf-8')).decode('utf-8')

        return default_internal_value


class RedisExecutionManifestSerializer(serializers.Serializer):
    user_info = RedisExecutionUserInfoSerializer()
    execution = RedisExecutionDetailsSerializer()
    context_id = serializers.CharField()
    ref_id = serializers.CharField()
    quotas = serializers.DictField(required=False, allow_empty=True, allow_null=True)
    metadata = serializers.DictField(required=False, allow_empty=True, allow_null=True)


class RedisExecutionEventSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[member.value for member in RedisExecutionEventTypes])
    created_at = serializers.DateTimeField()
    details = serializers.DictField(required=False, allow_empty=True, allow_null=True)


class RedisExecutionDataSerializer(RedisExecutionManifestSerializer):
    execution = None
    ref_id = serializers.CharField()
    status = serializers.ChoiceField(choices=[member.value for member in RedisExecutionStatus], required=False,
                                     allow_null=True)
    events = RedisExecutionEventSerializer(many=True, required=False, allow_null=True, allow_empty=True)
    stdout = serializers.ListField(child=serializers.CharField(allow_blank=True), required=False, allow_empty=True)
    stderr = serializers.ListField(child=serializers.CharField(allow_blank=True), required=False, allow_empty=True)

    def to_representation(self, instance):
        default_representation = super(RedisExecutionDataSerializer, self).to_representation(instance)

        ref_id = self.context.get('ref_id', None)
        if ref_id:
            default_representation.setdefault('ref_id', ref_id)

        return default_representation


class RedisExecutionManager(BaseExecutionManager):
    registry_index_name = 'schema-api-executions-data-idx'
    registry_key_prefix = 'schema-api:executions:data:'
    queue_key = 'schema-api:executions:queue'

    def _verify_data_index(self) -> None:
        schema = [
            TextField('$.ref_id', as_name='ref_id'),
            TextField('$.user_info.unique_id', as_name='user_id'),
            TextField('$.context_id', as_name='context_id'),
            NumericField('$.status', as_name='status')
        ]

        try:
            self.client.ft(self.registry_index_name).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=[self.registry_key_prefix], index_type=IndexType.JSON
                )
            )

        except redis.exceptions.ResponseError:
            pass
        self.index = self.client.ft(self.registry_index_name)

    def _create_client(self) -> redis.Redis:
        client = redis.Redis(host=self.host, port=self.port, decode_responses=True)
        response = client.ping()
        if not response:
            raise redis.ConnectionError('Unable to connect to Redis')

        return client

    @staticmethod
    def _to_schema_status(status: RedisExecutionStatus) -> TaskStatus:
        status_map = {
            RedisExecutionStatus.QUEUED: TaskStatus.QUEUED,
            RedisExecutionStatus.SCHEDULED: TaskStatus.SCHEDULED,
            RedisExecutionStatus.INITIALIZING: TaskStatus.INITIALIZING,
            RedisExecutionStatus.RUNNING: TaskStatus.RUNNING,
            RedisExecutionStatus.TERMINATING: TaskStatus.RUNNING,
            RedisExecutionStatus.COMPLETED: TaskStatus.COMPLETED,
            RedisExecutionStatus.CANCELED: TaskStatus.CANCELED,
            RedisExecutionStatus.ERROR: TaskStatus.ERROR,
            RedisExecutionStatus.EVICTED: TaskStatus.ERROR
        }
        return status_map[status]

    @staticmethod
    def _deserialize_status_data(redis_execution_data: RedisExecutionData) -> List[Tuple[TaskStatus, datetime]]:
        events = redis_execution_data.events
        status_updates = [
            (
                RedisExecutionManager._to_schema_status(RedisExecutionStatus(e['details']['status'])),
                parser.parse(e['created_at'])
            )
            for e in events
            if e['type'] == RedisExecutionEventTypes.STATUS_UPDATED.value
        ]

        return status_updates

    def __init__(self, host: str, port: int = 6379):
        self.host = host
        self.port = port
        self.client = self._create_client()

        self._verify_data_index()

    def submit(self, execution_manifest: ExecutionManifest) -> str:
        redis_execution_data_payload = {
            'user_info': execution_manifest.user_info,
            'context_id': execution_manifest.context_id,
        }
        if execution_manifest.quotas:
            redis_execution_data_payload['quotas'] = execution_manifest.quotas
        if execution_manifest.metadata:
            redis_execution_data_payload['metadata'] = execution_manifest.metadata
        redis_execution_data = RedisExecutionData(execution=execution_manifest.execution,
                                                  **redis_execution_data_payload)

        status_update_event = RedisExecutionEvent(type=RedisExecutionEventTypes.STATUS_UPDATED,
                                                  created_at=datetime.now(),
                                                  details={'status': RedisExecutionStatus.QUEUED}
                                                  )
        redis_execution_data.events.append(status_update_event)
        redis_execution_data.status = RedisExecutionStatus.QUEUED

        ref_id = redis_execution_data.ref_id

        redis_execution_data_serializer = RedisExecutionDataSerializer(redis_execution_data)
        registered_execution_data = redis_execution_data_serializer.data
        self.client.json().set(
            f'{self.registry_key_prefix}{ref_id}', '$',
            registered_execution_data
        )

        redis_execution_manifest_serializer = RedisExecutionManifestSerializer(redis_execution_data)
        queued_data = json.dumps(redis_execution_manifest_serializer.data)
        self.client.lpush(
            self.queue_key, queued_data
        )

        return ref_id

    def get(self, ref_id: str) -> LiveExecutionData:
        execution_data = self.client.json().get(
            f'{self.registry_key_prefix}{ref_id}',
            Path('.status'), Path('.events'), Path('.stdout'), Path('.stderr')
        )

        stdout = execution_data.pop('.stdout', [])
        stderr = execution_data.pop('.stderr', [])

        live_execution_status = RedisExecutionManager._deserialize_status_data(execution_data)

        return LiveExecutionData(status=live_execution_status, stdout=stdout, stderr=stderr)

    def get_status_history(self, ref_id: str) -> List[Tuple[TaskStatus, datetime]]:
        status_data = self.client.json().get(
            f'{self.registry_key_prefix}{ref_id}',
            Path('.status'), Path('.events')
        )
        if not status_data:
            raise ApplicationMissingExecutionError(
                f'Expected to find data for execution "{ref_id}" but no data was found'
            )

        return RedisExecutionManager._deserialize_status_data(status_data)

    def get_stdout(self, ref_id: str) -> List[str]:
        stdout = self.client.json().get(f'{self.registry_key_prefix}{ref_id}', Path('.stdout'))
        if not stdout:
            raise ApplicationMissingExecutionError(
                f'Expected to find data for execution "{ref_id}" but no data was found'
            )
        return stdout

    def get_stderr(self, ref_id: str) -> List[str]:
        stderr = self.client.json().get(f'{self.registry_key_prefix}{ref_id}', Path('.stderr'))
        if not stderr:
            raise ApplicationMissingExecutionError(
                f'Expected to find data for execution "{ref_id}" but no data was found'
            )
        return stderr

    def list(self, ref_ids: List[str] = None, statuses: List[TaskStatus] = None, user_id: str = None,
             context_id=None) -> List[Tuple[str, LiveExecutionData]]:
        filters = []

        if ref_ids:
            f = ' | '.join(['"{}"'.format(r) for r in ref_ids])
            filters.append('@ref_id:({})'.format(f))

        if statuses:
            f = ' | '.join(['@status[{} {}]'.format(s, s) for s in statuses])
            filters.append('({})'.format(f))

        if user_id:
            filters.append('@user_id:"{}"'.format(user_id))

        if context_id:
            filters.append('@context_id:"{}"'.format(user_id))

        if filters:
            result = self.index.search(Query(' '.join(filters)))
        else:
            result = self.index.search(Query("*"))

        live_execution_data_list = []

        for d in result.docs:
            redis_execution_data_serializer = RedisExecutionDataSerializer(data=json.loads(d.json))
            # ISSUE: How to treat cases where unexpected format is found in the execution data registry
            redis_execution_data_serializer.is_valid(raise_exception=True)
            raw_redis_execution_data = redis_execution_data_serializer.validated_data

            user_info = UserInfo(**raw_redis_execution_data.pop('user_info'))
            events = [RedisExecutionEvent(**e) for e in raw_redis_execution_data.pop('events')]

            redis_execution_data = RedisExecutionData(user_info=user_info, events=events, **raw_redis_execution_data)

            status_history = [(RedisExecutionManager._to_schema_status(e.details['status']), e.created_at)
                              for e in redis_execution_data.events
                              if e.type == RedisExecutionEventTypes.STATUS_UPDATED.value]

            live_execution_data = LiveExecutionData(stdout=redis_execution_data.stdout,
                                                    stderr=redis_execution_data.stderr, status_history=status_history)

            live_execution_data_list.append((redis_execution_data.ref_id, live_execution_data))

            if raw_redis_execution_data['status'] in [RedisExecutionStatus.ERROR, RedisExecutionStatus.CANCELED,
                                                      RedisExecutionStatus.EVICTED, RedisExecutionStatus.COMPLETED]:
                self.cancel(raw_redis_execution_data['ref_id'])

        return live_execution_data_list

    def update_quotas(self, ref_id: str):
        pass

    def cancel(self, ref_id: str):
        self.client.json().delete(f'{self.registry_key_prefix}{ref_id}')
