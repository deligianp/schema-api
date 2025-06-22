import importlib
import inspect
import logging
import os
from collections import OrderedDict

import dpath
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
        MANAGERS = self.load_managers()

    def load_managers(self):
        from core.serializers import ManagerConfigFileSerializer

        managers = {}
        manager_config_path = settings.MANAGER_CONFIG_PATH
        if not manager_config_path or not os.path.exists(manager_config_path):
            return

        with open(manager_config_path, 'r') as f:
            managers_config_data = yaml.load(f, Loader=yaml.SafeLoader)

        manager_serializer = ManagerConfigFileSerializer(data=managers_config_data, allow_null=True)
        manager_serializer.is_valid(raise_exception=True)

        validated_data = manager_serializer.validated_data
        managers = self.parse_managers_configuration(validated_data)
        return managers

    def discover_workflow_manager(self, path: str):
        try:
            module_path, class_name = path.rsplit('.', 1)
        except ValueError:
            module_path = ''
            class_name = path

        if not module_path:
            module_path = 'core.managers'
            class_name = path.split('.', 1)[0]

        try:
            module = importlib.import_module(module_path)
            try:
                return next(
                    obj for name, obj in inspect.getmembers(module, inspect.isclass)
                    if name == class_name
                )
            except StopIteration as si:
                raise ImportError from si
        except ImportError as ie:
            raise ImproperlyConfigured(f'Defined workflow manager "{path}" cannot be found.') from ie

    def parse_managers_configuration(self, managers_configuration):
        from workflows.constants import WorkflowLanguages

        manager_registry = {
            'tasks': None,
            'supported_versions': dict(),
            'managers': dict()
        }
        if managers_configuration:
            for manager_config in managers_configuration.get('managers', []):
                if not manager_config['enabled']:
                    continue
                name = manager_config['name']
                manager_class = self.discover_workflow_manager(manager_config['class_path'])
                use_definition = dpath.get(manager_config, 'configuration/workflows/use_definition', default=False)

                try:
                    workflow_manager_options = dpath.values(
                        settings.WORKFLOWS, f'MANAGER_ARGS/{name}'
                    )[0]
                except IndexError:
                    workflow_manager_options = {}
                workflow_manager = manager_class(**workflow_manager_options)

                manager_registry['managers'][name] = {
                    'manager_ref': workflow_manager,
                    'use_definition': use_definition
                }

                languages_config = dpath.values(manager_config, 'configuration/workflows/languages/*')
                for l in languages_config:
                    try:
                        language = WorkflowLanguages(value=l['language'])
                    except ValueError:
                        logger.warning(
                            f'Manager {name} defines an unsupported workflow language: {l["language"]}')
                        continue
                    versions = l['versions']
                    manager_registry['supported_versions'].setdefault(language, OrderedDict())
                    manager_registry['supported_versions'][language].setdefault(versions, list())
                    manager_registry['supported_versions'][language][versions].append(name)

                # Set the manager to be delegated tasks only if it is the first manager that is defined to do so
                if not manager_registry['tasks'] and \
                        dpath.get(manager_config, 'configuration/delegate_tasks', default=False):
                    manager_registry['tasks'] = name

        return manager_registry
