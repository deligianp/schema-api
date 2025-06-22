from typing import Optional, Tuple, Dict, Set

from semantic_version import NpmSpec

from core.apps import MANAGERS
from workflows.constants import WorkflowLanguages


def get_qualified_workflow_manager(language: WorkflowLanguages, version: str) -> Tuple[
    Optional[Dict], Optional[str]]:
    supported_versions = MANAGERS['supported_versions'].get(language, None)
    if not supported_versions:
        return None, None

    for v, supporting_manager_names in supported_versions.items():
        npm_spec = NpmSpec(v)
        if version is None or version in npm_spec:
            qualified_manager_name = supporting_manager_names[0]
            return MANAGERS['managers'][qualified_manager_name], qualified_manager_name

    return None, None