import base64
import dataclasses
import uuid
from abc import abstractmethod, ABC
from datetime import datetime
from typing import Dict, Optional, List, Tuple

from semantic_version import Version

from api.constants import TaskStatus
from workflows.constants import WorkflowLanguages


@dataclasses.dataclass
class UserInfo:
    unique_id: str
    username: Optional[str] = None
    fs_user_dir: Optional[str] = None


@dataclasses.dataclass
class ExecutionDetails:
    definition: str
    is_task: Optional[bool] = True
    language: Optional[WorkflowLanguages] = None
    version: Optional[Version] = None


@dataclasses.dataclass
class ExecutionManifest:
    execution: ExecutionDetails
    user_info: UserInfo
    context_id: str
    quotas: Optional[Dict] = None
    metadata: Optional[Dict] = None


@dataclasses.dataclass
class LiveExecutionData:
    status_history: Optional[List[Tuple[TaskStatus, datetime]]] = dataclasses.field(default_factory=list)
    stdout: Optional[List[str]] = dataclasses.field(default_factory=list)
    stderr: Optional[List[str]] = dataclasses.field(default_factory=list)


class BaseExecutionManager(ABC):

    @abstractmethod
    def submit(self, execution_manifest: ExecutionManifest) -> str:
        pass

    @abstractmethod
    def get(self, ref_id: str) -> LiveExecutionData:
        pass

    @abstractmethod
    def get_status_history(self, ref_id: str) -> List[Tuple[TaskStatus, datetime]]:
        pass

    @abstractmethod
    def get_stdout(self, ref_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_stderr(self, ref_id: str) -> List[str]:
        pass

    @abstractmethod
    def list(self, ref_ids: List[str] = None, statuses: List[TaskStatus] = None) -> List[Tuple[str, LiveExecutionData]]:
        pass

    @abstractmethod
    def update_quotas(self, ref_id: str):
        pass

    @abstractmethod
    def cancel(self, ref_id: str):
        pass
