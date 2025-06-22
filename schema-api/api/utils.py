from core.apps import MANAGERS
from core.managers.base import BaseExecutionManager
from core.utils import get_manager


def get_task_manager() -> str:
    return MANAGERS['tasks']
