import re
from dateutil.relativedelta import relativedelta


def parse_duration(descriptor):
    match = re.match(
        r'^((\d+) ?(years?|y) ?)?((\d+) ?(months?|m) ?)?((\d+) ?(weeks?|w) ?)?((\d+) ?(days?|d))?$',
        descriptor, re.IGNORECASE
    )
    if match is None:
        raise ValueError(f'String "{descriptor}" is not a valid duration descriptor')
    years = int(match.group(2)) if match.groups()[2] is not None else 0
    months = int(match.group(5)) if match.groups()[5] is not None else 0
    weeks = int(match.group(8)) if match.groups()[8] is not None else 0
    days = int(match.group(11)) if match.groups()[11] is not None else 0

    return relativedelta(years=years, months=months, weeks=weeks, days=days)
