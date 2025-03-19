import json
from copy import deepcopy

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet

from api.constants import TaskStatus
from api.models import Context
from core.apps import MANAGERS
from workflows.constants import WorkflowLanguages
from workflows.models import Workflow, WorkflowExecutor, WorkflowExecutorYield, WorkflowEnv, WorkflowInputMountPoint, \
    WorkflowOutputMountPoint, WorkflowResourceSet, WorkflowTag, WorkflowStatusLog, WorkflowSpecification
from workflows.parsers import NativeWorkflowManager


class WorkflowSpecificationService:

    def __init__(self, user: settings.AUTH_USER_MODEL, context: Context, language: WorkflowLanguages,
                 version: str = None):
        self.user = user
        self.context = context
        self.language = language
        self.version = version

    @transaction.atomic
    def execute_workflow_specification(self, specification: str):

        if self.language == WorkflowLanguages.NATIVE:
            native_workflow = json.loads(specification)
        # elif self.language == other workflow language:
        #   invoke language parser that produces native_workflow
        else:
            raise ValueError(
                'No parser was found for language {} (version: {})'.format(self.language, self.version or 'any'))

        workflow_service = WorkflowService(self.user, self.context)
        workflow = workflow_service.submit_workflow(**native_workflow, specification=specification)

        workflow_specification = WorkflowSpecification.objects.create(
            workflow=workflow, language=self.language, version=self.version if self.version else '', content=specification
        )

        workflow_managers = MANAGERS.get('workflows',{})
        candidate_managers = workflow_managers.get(self.language, [])

        if candidate_managers:
            if not self.version:
                qualified_manager = candidate_managers[0]

            else:
                # Take the first that supports the submitted workflow's version
                try:
                    qualified_manager = next(m for m in candidate_managers if self.version in m['versions'])
                except StopIteration:
                    raise Exception()

            manager = qualified_manager['class']()
            manager.run(specification if qualified_manager['use_definition'] else native_workflow)

            workflow_status_log_service = WorkflowStatusLogService(workflow=workflow)
            workflow_status_log_service.set_status(TaskStatus.SCHEDULED)

        return workflow


class WorkflowService:

    def __init__(self, user: settings.AUTH_USER_MODEL, context: Context):
        self.user = user
        self.context = context

    @transaction.atomic
    def submit_workflow(self, specification=None, **workflow_definition):

        # Validate and resolve order of execution
        layers = NativeWorkflowManager.validate(workflow_definition)

        if layers:
            execution_order = NativeWorkflowManager.resolve(workflow_definition, layers)
            workflow_definition['execution_order'] = str(execution_order)

        _workflow_definition = deepcopy(workflow_definition)

        # Store workflow data in database tables
        executors_data = workflow_definition.pop('executors')
        inputs_data = workflow_definition.pop('inputs', None)
        outputs_data = workflow_definition.pop('outputs', None)
        resources_data = workflow_definition.pop('resources', None)
        tags_data = workflow_definition.pop('tags', None)

        workflow = Workflow.objects.create(user=self.user, context=self.context, **workflow_definition)

        workflow_status_log_service = WorkflowStatusLogService(workflow=workflow)
        workflow_status_log_service.set_status(TaskStatus.SUBMITTED)

        for ex in executors_data:
            env_data = ex.pop('env', None)
            yields_data = ex.pop('yields', None)

            ex.pop('priority', None)

            executor = WorkflowExecutor.objects.create(workflow=workflow, **ex)

            if yields_data:
                for y in yields_data:
                    _yield = WorkflowExecutorYield.objects.create(executor=executor, **y)

            if env_data:
                for env in env_data:
                    env = WorkflowEnv.objects.create(executor=executor, **env)

        if inputs_data:
            for i in inputs_data:
                _input = WorkflowInputMountPoint.objects.create(workflow=workflow, **i)

        if outputs_data:
            for o in outputs_data:
                output = WorkflowOutputMountPoint.objects.create(workflow=workflow, **o)

        if resources_data:
            resources = WorkflowResourceSet.objects.create(workflow=workflow, **resources_data)

        if tags_data:
            for t in tags_data:
                tag = WorkflowTag.objects.create(workflow=workflow, **t)

        # Evaluate quotas

        workflow_status_log_service.set_status(TaskStatus.APPROVED)

        # Queue job for execution
        if WORKFLOW_MANAGER_CLASS:

            workflow_manager = WORKFLOW_MANAGER_CLASS(**settings.WORKFLOWS['MANAGER_OPTIONS'])
            workflow_manager.run(_workflow_definition, user=self.user, context=self.context)
            workflow_status_log_service.set_status(TaskStatus.SCHEDULED)

        workflow.refresh_from_db()

        return workflow

    @transaction.atomic
    def get_workflow(self, uuid):
        workflow = Workflow.objects.get(uuid=uuid)

        return workflow

    def get_workflows(self) -> QuerySet[Workflow]:
        return Workflow.objects.filter(user=self.user, context=self.context)

    @transaction.atomic
    def cancel(self, uuid: str) -> None:
        workflow = self.get_workflow(uuid)

        workflow_status_log_service = WorkflowStatusLogService(workflow=workflow)

        # Send cancellation event
        if WORKFLOW_MANAGER_CLASS:
            workflow_manager = WORKFLOW_MANAGER_CLASS(**settings.WORKFLOWS['MANAGER_OPTIONS'])
            workflow_manager.cancel(workflow.backend_ref)

        workflow_status_log_service = WorkflowStatusLogService(workflow=workflow)
        workflow_status_log_service.set_status(TaskStatus.CANCELED)


class WorkflowStatusLogService:

    def __init__(self, workflow: Workflow):
        self.workflow = workflow

    def set_status(self, status: TaskStatus, **optional) -> WorkflowStatusLog:
        return WorkflowStatusLog.objects.create(workflow=self.workflow, value=status, **optional)

    def get_current_status(self) -> WorkflowStatusLog:
        return WorkflowStatusLog.objects.filter(workflow=self.workflow).order_by('-status', '-created_at').first()
