import json
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import List, Optional, Tuple, Iterable

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.db.models import QuerySet, OuterRef, Subquery

from api.constants import TaskStatus
from api.models import Context
from core.managers.base import UserInfo, ExecutionDetails, ExecutionManifest
from core.utils import drop_none_values, get_manager
from util.exceptions import ApplicationWorkflowParsingError
from workflows.constants import WorkflowLanguages
from workflows.models import Workflow, WorkflowExecutor, WorkflowExecutorYield, WorkflowEnv, WorkflowInputMountPoint, \
    WorkflowOutputMountPoint, WorkflowResourceSet, WorkflowTag, WorkflowStatusLog, WorkflowDefinition
from workflows.parsers import SchemaNativeWorkflowParser
from workflows.serializers import WorkflowSerializer
from workflows.utils import get_qualified_workflow_manager


class WorkflowDefinitionService:

    def __init__(self, user: settings.AUTH_USER_MODEL, context: Context):
        self.user = user
        self.context = context

    @transaction.atomic
    def run_workflow(self, *, definition: str, language: WorkflowLanguages = WorkflowLanguages.SNWL,
                     version: str = None) -> Workflow:
        """
        Submit a workflow definition to be scheduled for execution.

        Args:
            definition (str): the workflow definition text
            language (WorkflowLanguages):
                optionally, the language or specification in which the workflow definition is written on. If not given,
                it is assumed as SNWL.
            version (str):
                optionally, the version of the specification in which the workflow definition is written on.
                If not given, no version is assumed and the selection of a transpiler will be made based solely on
                the workflow language.

        Returns:
            Workflow: the computed workflow as stored internally
        """

        # Check if the definition is already assumed as SNWL. If it is, just load the JSON. Else, find a proper
        # transpiler to produce the corresponding SNWL
        if language == WorkflowLanguages.SNWL:
            native_workflow = json.loads(definition)
        else:
            raise ApplicationWorkflowParsingError(
                f'Workflow definitions for language "{language}", of version "{version}" are not supported')

        # Initialize a WorkflowService for the given user, in the given context
        workflow_service = WorkflowService(self.user, self.context)

        workflow = workflow_service.submit_workflow(**native_workflow, definition=definition, language=language,
                                                    version=version)

        if settings.WORKFLOWS['STORE_DEFINITIONS']:
            workflow_definition_object = WorkflowDefinition.objects.create(
                workflow=workflow, language=language, version=version if version else '',
                content=definition
            )

        return workflow


class WorkflowService:

    def __init__(self, user: settings.AUTH_USER_MODEL, context: Context):
        self.user = user
        self.context = context

    def _construct_execution_manifest(self, *, definition: str, language: WorkflowLanguages = None,
                                      version: str = None) -> ExecutionManifest:
        user_info = UserInfo(unique_id=str(self.user.uuid), username=self.user.username,
                             fs_user_dir=self.user.profile.fs_user_dir)

        execution_details = ExecutionDetails(is_task=False, **drop_none_values(
            {
                'definition': definition,
                'language': language,
                'version': version
            }
        ))
        execution_manifest = ExecutionManifest(
            execution=execution_details,
            user_info=user_info,
            context_id=str(self.context.id)
        )

        return execution_manifest

    @transaction.atomic
    def submit_workflow(self, *, definition: str = None, language: WorkflowLanguages = WorkflowLanguages.SNWL,
                        version: str = None, **workflow_definition):

        # Validate and resolve order of execution
        execution_order: Optional[List[int]] = workflow_definition.pop('execution_order', None)
        if execution_order:
            SchemaNativeWorkflowParser.validate_order(workflow_definition, eval(execution_order))
        else:
            layers = SchemaNativeWorkflowParser.validate(workflow_definition)

            if layers:
                execution_order = SchemaNativeWorkflowParser.resolve(workflow_definition, layers)
        workflow_definition['execution_order'] = str(execution_order)

        workflow_manager_data, workflow_manager_name = get_qualified_workflow_manager(language, version)

        if not workflow_manager_name:
            raise ApplicationWorkflowParsingError(
                f'No proper managers are defined for the provided workflow specification: {language}'
                + f' v.{version}' if version else ''
            )

        _workflow_definition = deepcopy(workflow_definition)

        # Store workflow data in database tables
        executors_data = workflow_definition.pop('executors')
        inputs_data = workflow_definition.pop('inputs', None)
        outputs_data = workflow_definition.pop('outputs', None)
        resources_data = workflow_definition.pop('resources', None)
        tags_data = workflow_definition.pop('tags', None)

        workflow = Workflow.objects.create(user=self.user, context=self.context, **workflow_definition)

        workflow_status_log_service = WorkflowStatusLogService(workflow=workflow)
        workflow_status_log_service.log_status_update(TaskStatus.SUBMITTED)

        for ex in executors_data:
            env_data = ex.pop('env', None)
            yields_data = ex.pop('yields', None)

            ex.pop('priority', None)

            executor = WorkflowExecutor.objects.create(workflow=workflow, **ex)

            if yields_data:
                for y in yields_data:
                    _yield = WorkflowExecutorYield.objects.create(executor=executor, **y)

            if env_data:
                for e in env_data:
                    env = WorkflowEnv.objects.create(executor=executor, **e)

        if inputs_data:
            for i in inputs_data:
                _input = WorkflowInputMountPoint.objects.create(workflow=workflow, **i)

        if outputs_data:
            for o in outputs_data:
                output = WorkflowOutputMountPoint.objects.create(workflow=workflow, **o)

        if resources_data:
            resources = WorkflowResourceSet.objects.create(workflow=workflow, **resources_data)
        else:
            resources = WorkflowResourceSet.objects.create(workflow=workflow)
            pass

        if tags_data:
            for t in tags_data:
                tag = WorkflowTag.objects.create(workflow=workflow, **t)

        # Evaluate quotas
        workflow_status_log_service.log_status_update(TaskStatus.APPROVED)

        workflow_manager = workflow_manager_data['manager_ref']
        workflow_manager_use_definition = workflow_manager_data['use_definition']

        if workflow_manager_use_definition:
            execution_manifest = self._construct_execution_manifest(definition=definition, language=language,
                                                                    version=version)
        else:
            # native_definition_json = json.dumps(_workflow_definition)
            native_definition_json = json.dumps(WorkflowSerializer(workflow).data)
            execution_manifest = self._construct_execution_manifest(definition=native_definition_json,
                                                                    language=language, version=version)

        execution_uuid = workflow_manager.submit(execution_manifest)

        workflow.backend_ref = execution_uuid
        workflow.manager_name = workflow_manager_name
        workflow.save()

        workflow_status_log_service.log_status_update(TaskStatus.QUEUED)

        workflow.refresh_from_db()

        return workflow

    @transaction.atomic
    def get_workflow(self, uuid):
        workflow = self.get_workflows().get(uuid=uuid)

        return workflow

    @staticmethod
    @transaction.atomic
    def synchronize_dispatched_executions(workflows_qs: QuerySet[Workflow]):

        grouped = defaultdict(list)
        for w in workflows_qs:
            grouped[w.manager_name].append(w)

        for manager_name, manager_workflows in grouped.items():
            backend_refs = [w.backend_ref for w in manager_workflows]

            # ISSUE: Manager may not be available at subsequent deployments
            manager = get_manager(manager_name)

            # ISSUE: If returned data does not cover all queryset items, execution may get silently stuck with no update
            live_data_map = dict(manager.list(ref_ids=backend_refs))

            for w in manager_workflows:
                workflow_live_data = live_data_map[w.backend_ref]

                workflow_status_log_service = WorkflowStatusLogService(w)
                workflow_status_log_service.update_live_data(workflow_live_data.status_history)

    def get_workflows(self) -> QuerySet[Workflow]:
        return Workflow.objects.filter(user=self.user, context=self.context)

    @transaction.atomic
    def cancel(self, uuid: str) -> None:
        workflow = self.get_workflow(uuid)

        workflow_status_log_service = WorkflowStatusLogService(workflow=workflow)

        if not workflow_status_log_service.is_workflow_pending():
            return

        # If manager no longer exists in configuration, then raise an uncaught error
        # Probably will have to change it in the future
        manager = get_manager(workflow.manager_name)

        manager.cancel(workflow.backend_ref)
        workflow_status_log_service.log_status_update(TaskStatus.CANCELED, avoid_duplicates=True)


class WorkflowStatusLogService:

    def __init__(self, workflow: Workflow):
        self.workflow = workflow

    @staticmethod
    def filter_workflows_by_status(queryset: QuerySet[Workflow], statuses: Iterable[TaskStatus]) -> QuerySet[
        Workflow]:

        latest_statuses = WorkflowStatusLog.objects.filter(
            workflow=OuterRef('pk')
        ).order_by('-status','-created_at')

        workflows_with_latest_status = queryset.annotate(
            latest_status=Subquery(latest_statuses.values('status')[:1])
        )

        return workflows_with_latest_status.filter(latest_status__in=statuses)

    @transaction.atomic
    def update_live_data(self, live_status_history: List[Tuple[TaskStatus, datetime]]):
        for sl in live_status_history:
            self.log_status_update(sl[0], created_at=sl[1], avoid_duplicates=True)

    def log_status_update(self, status: TaskStatus, avoid_duplicates: bool = False, **optional) -> WorkflowStatusLog:
        if avoid_duplicates:
            try:
                workflow_status_log, created = WorkflowStatusLog.objects.get_or_create(
                    workflow=self.workflow, status=status, defaults={
                        **optional,
                        "workflow": self.workflow,
                        "status": status
                    }
                )
                return workflow_status_log
            except MultipleObjectsReturned:
                return WorkflowStatusLog.objects.filter(workflow=self.workflow, status=status).order_by(
                    '-created_at').first()
        else:
            return WorkflowStatusLog.objects.create(workflow=self.workflow, status=status, **optional)

    def get_current_status(self) -> WorkflowStatusLog:
        return WorkflowStatusLog.objects.filter(workflow=self.workflow).order_by('-status', '-created_at').first()

    def is_workflow_pending(self) -> bool:
        current_status = self.get_current_status()
        return TaskStatus.SUBMITTED <= current_status.status <= TaskStatus.RUNNING

    def is_workflow_dispatched(self) -> bool:
        current_status = self.get_current_status()
        return TaskStatus.QUEUED <= current_status.status <= TaskStatus.RUNNING

    def does_workflow_await_dispatch(self):
        current_status = self.get_current_status()
        return TaskStatus.SUBMITTED <= current_status.status < TaskStatus.QUEUED
