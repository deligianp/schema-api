import importlib
import inspect
import logging
import os

import yaml
from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MANAGERS = dict()

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        global MANAGERS
        from core.serializers import ManagerConfigFileSerializer

        managers = {
            'tasks': [],
            'workflows': {}
        }
        manager_config_path = settings.MANAGER_CONFIG_PATH
        if not manager_config_path or not os.path.exists(manager_config_path):
            return

        with open(manager_config_path, 'r') as f:
            managers_config_data = yaml.load(f, Loader=yaml.SafeLoader)

        manager_serializer = ManagerConfigFileSerializer(data=managers_config_data, allow_null=True)
        manager_serializer.is_valid(raise_exception=True)

        validated_data = manager_serializer.validated_data
        if validated_data:
            for manager_config in validated_data['managers']:
                tasks_config = self.parse_task_manager_configuration(manager_config)

                managers.setdefault('tasks', [])
                managers['tasks'].extend(tasks_config)

                workflows_config = self.parse_workflow_manager_configuration(manager_config)

                managers.setdefault('workflows', {})
                managers['workflows'] = {
                    l: managers['workflows'].get(l, []) + (workflows_config[l])
                    for l in workflows_config
                }

        if managers['tasks']:
            task_managers_descriptors = [
                f'- {m["name"]} at {m["class"].__module__}.{m["class"].__name__}' for m in managers['tasks']
            ]
            logger.debug('Mapped managers for tasks: \n'
                         '{}'.format('\n'.join(task_managers_descriptors)))

        if managers['workflows']:
            workflow_managers_descriptors = [
                f'- for {l} (versions: {m["versions"]}), {m["name"]} at {m["class"].__module__}.{m["class"].__name__}'
                for l in managers['workflows'] for m in managers['workflows'][l]
            ]

            logger.debug('Mapped managers for workflows: \n'
                         '{}'.format('\n'.join(workflow_managers_descriptors)))
        MANAGERS = managers

    def discover_workflow_manager(self, path: str):
        from core.managers import BaseWorkflowManager
        try:
            module_path, class_name = path.rsplit('.', 1)
        except ValueError:
            module_path = ''
            class_name = path

        if not module_path:
            module_path = 'workflows.managers'
            class_name = path.split('.', 1)[0]

        try:
            module = importlib.import_module(module_path)
            try:
                return next(
                    obj for name, obj in inspect.getmembers(module, inspect.isclass)
                    if name == class_name and issubclass(obj, BaseWorkflowManager)
                    and obj is not BaseWorkflowManager
                )
            except StopIteration as si:
                raise ImportError from si
        except ImportError as ie:
            raise ImproperlyConfigured(f'Defined workflow manager "{path}" cannot be found.') from ie

    def parse_task_manager_configuration(self, manager_configuration):
        name = manager_configuration['name']
        enabled = manager_configuration['enabled']
        if not enabled:
            return

        try:
            use_for_tasks = manager_configuration['configuration']['tasks']
        except KeyError:
            return None

        if not use_for_tasks:
            return None

        manager_class = self.discover_workflow_manager(manager_configuration['class_path'])

        return [
            {
                'name': name,
                'class': manager_class,
            }
        ]

    def parse_workflow_manager_configuration(self, manager_configuration):
        from workflows.constants import WorkflowLanguages

        workflow_managers = dict()
        name = manager_configuration['name']
        enabled = manager_configuration['enabled']
        if not enabled:
            return

        try:
            languages_config = manager_configuration['configuration']['workflows']['languages']
        except KeyError:
            return

        for language_config in languages_config:
            try:
                language = WorkflowLanguages(value=language_config['language'])
            except ValueError:
                logger.warning(
                    f'Manager {name} defines an unsupported workflow language: {language_config["language"]}')
                continue

            manager_class = self.discover_workflow_manager(manager_configuration['class_path'])

            workflow_managers.setdefault(language, [])
            workflow_managers[language].append({
                "name": name,
                "class": manager_class,
                "versions": language_config['versions'],
                'use_definition': language_config['use_definition'],
            }
            )
        return workflow_managers
