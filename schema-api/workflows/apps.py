import importlib
import inspect

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

WORKFLOW_MANAGER_CLASS = None

class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workflows'

    def ready(self):
        from core.managers import BaseWorkflowManager

        manager_class_path = settings.WORKFLOWS['MANAGER_CLASS_PATH']
        if not manager_class_path:
            return

        try:
            module_path, class_name = manager_class_path.rsplit('.', 1)
        except ValueError:
            module_path = ''
            class_name = manager_class_path

        if not module_path:
            module_path = 'workflows.managers'
            class_name = manager_class_path.split('.', 1)[0]

        try:
            module = importlib.import_module(module_path)
            try:
                global WORKFLOW_MANAGER_CLASS
                WORKFLOW_MANAGER_CLASS = next(
                    obj for name, obj in inspect.getmembers(module, inspect.isclass)
                    if name == class_name and issubclass(obj, BaseWorkflowManager)
                    and obj is not BaseWorkflowManager
                )
            except StopIteration as si:
                raise ImportError from si
        except ImportError as ie:
            raise ImproperlyConfigured(f'Defined workflow manager "{manager_class_path}" cannot be found.') from ie
