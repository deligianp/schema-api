from django.conf import settings
from django.db import models

from api.constants import TaskStatus
from api.models import Context
from core.models import BaseSchedulable, BaseExecutor, BaseEnv, BaseInputMountPoint, BaseMountPoint, BaseResourceSet, \
    BaseTag
from util.defaults import get_current_datetime


# Create your models here.
class Workflow(BaseSchedulable):
    # user: The user that has submitted the schedulable. It can be null for cases where a schedulable may not record its
    # user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    # context: The context in which the schedulable was submitted. It can be null for cases where a schedulable may not
    # record its context
    context = models.ForeignKey(Context, null=True, on_delete=models.SET_NULL)
    execution_order = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(default=get_current_datetime)


class WorkflowStatusLog(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='status_logs')
    value = models.IntegerField(choices=TaskStatus.choices)
    created_at = models.DateTimeField(default=get_current_datetime)


class WorkflowExecutor(BaseExecutor):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executors')


class WorkflowEnv(BaseEnv):
    executor = models.ForeignKey(WorkflowExecutor, on_delete=models.CASCADE, related_name='env')


class WorkflowExecutorYield(models.Model):
    executor = models.ForeignKey(WorkflowExecutor, on_delete=models.CASCADE, related_name='yields')
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)

class WorkflowInputMountPoint(BaseInputMountPoint):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='inputs')
    path = None
    name = models.CharField(max_length=255)


class WorkflowOutputMountPoint(BaseMountPoint):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='outputs')
    path = None
    name = models.CharField(max_length=255)



class WorkflowResourceSet(BaseResourceSet):
    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE, related_name='resources')


class WorkflowTag(BaseTag):
    workflow = models.ManyToManyField(Workflow, related_name='tags')
