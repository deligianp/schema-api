from django.utils.timezone import now
from rest_framework import status
from rest_framework.response import Response


class QuotaViolationError(Exception):

    def __init__(self, resource: str, is_context_violation: bool, is_severe:bool, evaluation_time=None, current=None, limit=None, requested=None, reason=None):
        self.resource = resource
        self.is_context_violation = is_context_violation
        self.is_severe = is_severe
        if not evaluation_time:
            evaluation_time = now()
        self.evaluation_time = evaluation_time
        if limit and requested:
            self.state = dict()
            if current:
                self.state['current'] = current
            self.state['requested'] = requested
            self.state['limit'] = limit
        if reason:
            self.reason = reason

        super(QuotaViolationError, self).__init__()


def custom_exception_handler(exc: QuotaViolationError, context):
    data = {
        'resource': exc.resource,
        'ts_evaluation': exc.evaluation_time,
        'level': 'context' if exc.is_context_violation else 'participation',
        'severity': 'permanent' if exc.is_severe else 'temporary'
    }
    if hasattr(exc, 'state'):
        data['details'] = exc.state
    if hasattr(exc, 'reason'):
        data['reason'] = exc.reason
    return Response(status=status.HTTP_403_FORBIDDEN, data=data)


class QuotaSoftViolationError(QuotaViolationError):

    def __init__(self, resource: str, is_context_violation: bool, evaluation_time=None, current=None, limit=None, requested=None, reason=None):
        super(QuotaSoftViolationError, self).__init__(resource, is_context_violation, False, evaluation_time=evaluation_time, current=current, limit=limit, requested=requested, reason=reason)


class QuotaHardViolationError(QuotaViolationError):

    def __init__(self, resource: str, is_context_violation: bool, evaluation_time=None, current=None, limit=None, requested=None, reason=None):
        super(QuotaHardViolationError, self).__init__(resource, is_context_violation, True, evaluation_time=evaluation_time, current=current, limit=limit, requested=requested, reason=reason)
