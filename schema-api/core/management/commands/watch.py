import json
import logging.config
import sys
import time
from argparse import ArgumentParser
from typing import Any, Dict

from django.db.models import QuerySet, Func, IntegerField, F

from api.constants import TaskStatus
from api.models import Task
from api.services import TaskStatusLogService, TaskService
from core.utils import get_manager
from util.commands import ApplicationBaseCommand
from util.logging import get_logging_config, get_logging_level_by_verbosity
from workflows.models import Workflow
from workflows.services import WorkflowService, WorkflowStatusLogService

logging.config.dictConfig(get_logging_config())
logger = logging.getLogger(__name__)


class Command(ApplicationBaseCommand):
    help = 'Periodically watch for updates in dispatched executions and update the connected database'

    def add_arguments(self, parser: ArgumentParser):
        subparsers = parser.add_subparsers(help='sub-command help', dest='command0')

        executions_parser = subparsers.add_parser('executions', help='Watch for updates in dispatched executions')
        executions_parser.add_argument(
            'index', help='Index of the worker within the worker set', type=int, default=0, nargs="?"
        )
        executions_parser.add_argument(
            'total', help='Total number of workers in worker set', type=int, default=1, nargs="?"
        )
        executions_parser.add_argument('-i', '--interval', help='Number of seconds before each worker '
                                                                'invocation', type=int)
        executions_parser.add_argument('-l', '--limit', help='Maximum number of executions managed in '
                                                             'each iteration', type=int)
        executions_parser.add_argument('-m', '--managers', help='Names of managers for which this worker '
                                                                'set will manage their executions', nargs='+')

    def validate_arguments(self, **options: Dict[str, Any]) -> Dict[str, Any]:
        if options['index'] < 0:
            raise ValueError('Worker index must be greater than or equal to zero')

        if options['total'] < 1:
            raise ValueError('Total workers must be greater than or equal to 1')

        if options['index'] >= options['total']:
            raise ValueError(
                f'Index value {options["index"]} is greater than maximum expected index of {options["total"] - 1}'
            )

        if interval := options.get('interval', None):
            if interval < 1:
                raise ValueError('Interval in seconds, must be greater than or equal to 1s')

        if limit := options.get('limit', None):
            if limit < 1:
                raise ValueError('Limit must be greater than or equal to 1')

        if manager_names := options.get('managers', None):
            for m in manager_names:
                # Just call it to make sure the managers exist
                get_manager(m)

        return options

    def get_related_workflows(self, **options: Dict[str, Any]) -> QuerySet[Workflow]:
        target_statuses = [TaskStatus.QUEUED, TaskStatus.INITIALIZING, TaskStatus.RUNNING, TaskStatus.SCHEDULED]
        dispatched_workflows = WorkflowStatusLogService.filter_workflows_by_status(
            Workflow.objects.all(),
            target_statuses
        )

        related_workflows = dispatched_workflows.annotate(
            worker_idx=Func(F("id"), options['total'], function="MOD", output_field=IntegerField())
        ).filter(worker_idx=options['index'])

        if manager_names := options.get('managers', None):
            related_workflows = related_workflows.filter(manager_name__in=manager_names)

        if limit := options.get('limit', None):
            return related_workflows[:limit]
        return related_workflows

    def get_related_tasks(self, **options: Dict[str, Any]) -> QuerySet[Task]:
        target_statuses = [TaskStatus.QUEUED, TaskStatus.INITIALIZING, TaskStatus.RUNNING, TaskStatus.SCHEDULED]
        dispatched_tasks = TaskStatusLogService.filter_tasks_by_status(
            Task.objects.all(),
            target_statuses
        )

        related_tasks = dispatched_tasks.annotate(
            worker_idx=Func(F("id"), options['total'], function="MOD", output_field=IntegerField())
        ).filter(worker_idx=options['index'])

        if manager_names := options.get('managers', None):
            related_tasks = related_tasks.filter(manager_name__in=manager_names)

        if limit := options.get('limit', None):
            return related_tasks[:limit]
        return related_tasks

    def handle(self, *args, **options):
        logger.setLevel(get_logging_level_by_verbosity(options['verbosity']))

        try:
            logger.debug('Validating arguments...')
            args = self.validate_arguments(**options)

            logger.debug(f'Validated arguments: {json.dumps(args, indent=2)}')

            repeat = True
            if bool(args.get('interval', None)):
                logger.info('Starting service to watch for live data updates')
            else:
                logger.info('Retrieving live data on demand')
            try:
                while repeat:

                    s = time.perf_counter()
                    workflows = self.get_related_workflows(**args)
                    e = time.perf_counter()
                    workflows_query_time = e - s
                    logger.info(f'Found {len(workflows)} dispatched workflow executions for which will check live data')

                    s = time.perf_counter()
                    tasks = self.get_related_tasks(**args)
                    e = time.perf_counter()
                    tasks_query_time = e - s
                    logger.info(f'Found {len(tasks)} dispatched task executions for which will check live data')

                    logger.info(f'Updating workflows')
                    s = time.perf_counter()
                    WorkflowService.synchronize_dispatched_executions(workflows)
                    e = time.perf_counter()
                    workflows_update_time = e - s

                    logger.info(f'Updating tasks')
                    s = time.perf_counter()
                    TaskService.synchronize_dispatched_executions(tasks)
                    e = time.perf_counter()
                    tasks_update_time = e - s

                    logger.info(f'Round accumulated query time: {workflows_query_time + tasks_query_time:.6f}s')
                    logger.info(f'Round accumulated update time: {workflows_update_time + tasks_update_time:.6f}s')

                    repeat = bool(args.get('interval', None))
                    if repeat:
                        logger.debug(f'Resting for {options["interval"]} seconds...')
                        time.sleep(options['interval'])
            except KeyboardInterrupt as ke:
                if not bool(args.get('interval', None)):
                    raise KeyboardInterrupt from ke
                logger.info('Terminating signal caught. Exiting...')
                sys.exit(0)


        except Exception as e:
            logger.critical(e, exc_info=True)
            sys.exit(1)
