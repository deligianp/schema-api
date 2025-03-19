import re


def normalize_version_definition(version: str) -> str:
    match = re.match(r'^v?(\d+(\.\d+){0,2})(-.*)*$', version)
    if not match:
        raise ValueError('Invalid version definition')
    defined_version = match.group(1)
    segments = defined_version.split('.')
    normalization = ['0'] * (3 - len(segments))
    segments.extend(normalization)
    return '.'.join(segments)