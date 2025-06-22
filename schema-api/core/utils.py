import re
from typing import Dict, Set

from core.apps import MANAGERS
from core.managers.base import BaseExecutionManager


def normalize_version_definition(version: str) -> str:
    match = re.match(r'^v?(\d+(\.\d+){0,2})(-.*)*$', version)
    if not match:
        raise ValueError('Invalid version definition')
    defined_version = match.group(1)
    segments = defined_version.split('.')
    normalization = ['0'] * (3 - len(segments))
    segments.extend(normalization)
    return '.'.join(segments)


def drop_none_values(dictionary: Dict, exception_fields: Set[str] = None, reference_level='') -> Dict:
    if not exception_fields:
        exception_fields = set()

    resulting_dict = dict()

    reference_level = reference_level.strip(".")

    for k, v in dictionary.items():
        current_reference_key = k if not reference_level else f'{reference_level}.{k}'
        if isinstance(v, dict):
            v = drop_none_values(v, exception_fields, reference_level=current_reference_key)
        print(f'{current_reference_key}: {v}')
        try:
            if len(v) > 0 or k in exception_fields:
                resulting_dict[k] = v
        except TypeError:
            if v is not None or current_reference_key in exception_fields:
                resulting_dict[k] = v

    return resulting_dict


def get_manager(name: str) -> BaseExecutionManager:
    manager = MANAGERS['managers'].get(name, None)

    if not manager:
        raise ValueError(f'Unknown manager {name}')

    return manager['manager_ref']
