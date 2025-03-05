from typing import Dict, Tuple, Any

from django.conf import settings

from api.constants import TaskStatus
from api.models import Context
from core.managers import BaseWorkflowManager
from quotas.models import Quotas


class SynchronousTesWorkflowManager(BaseWorkflowManager):

    def update_quotas(self, ref_id: str):
        pass

    def run(self, definition: Dict, user: settings.AUTH_USER_MODEL = None, context: Context = None,
            quotas: Dict[str, Quotas] = None) -> Tuple[bool, Any]:
        pass

    def get(self, ref_id: str) -> Dict:
        pass

    def get_status(self, ref_id: str) -> TaskStatus:
        pass

    def get_stdout(self, ref_id: str) -> str:
        pass

    def get_stderr(self, ref_id: str) -> str:
        pass

    def list(self):
        pass

    def cancel(self, ref_id: str):
        pass


class RedisQueueWorkflowManager(BaseWorkflowManager):

    def update_quotas(self, ref_id: str):
        pass

    def run(self, definition: Dict, user: settings.AUTH_USER_MODEL = None, context: Context = None,
            quotas: Dict[str, Quotas] = None) -> Tuple[bool, Any]:
        pass

    def get(self, ref_id: str) -> Dict:
        pass

    def get_status(self, ref_id: str) -> TaskStatus:
        pass

    def get_stdout(self, ref_id: str) -> str:
        pass

    def get_stderr(self, ref_id: str) -> str:
        pass

    def list(self):
        pass

    def cancel(self, ref_id: str):
        pass
