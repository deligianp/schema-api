from abc import abstractmethod, ABC
from typing import Dict, Tuple, Any

from django.conf import settings

from api.constants import TaskStatus
from api.models import Context
from quotas.models import Quotas


class BaseExecutionManager(ABC):

    @abstractmethod
    def run(self, definition: Dict, user: settings.AUTH_USER_MODEL = None, context: Context = None,
            quotas: Dict[str, Quotas] = None) -> Tuple[bool, Any]:
        pass

    @abstractmethod
    def get(self, ref_id: str) -> Dict:
        pass

    @abstractmethod
    def get_status(self, ref_id: str) -> TaskStatus:
        pass

    @abstractmethod
    def get_stdout(self, ref_id: str) -> str:
        pass

    @abstractmethod
    def get_stderr(self, ref_id: str) -> str:
        pass

    @abstractmethod
    def list(self):
        pass

    @abstractmethod
    def update_quotas(self, ref_id: str):
        pass

    @abstractmethod
    def cancel(self, ref_id: str):
        pass


class BaseWorkflowManager(BaseExecutionManager, ABC):
    pass


class BaseTaskManager(BaseExecutionManager, ABC):
    pass
