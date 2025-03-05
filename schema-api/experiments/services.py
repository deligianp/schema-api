from typing import Iterable

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import QuerySet

from api.models import Context, Task
from experiments.models import Experiment
from util.exceptions import ApplicationValidationError, ApplicationDuplicateError, ApplicationNotFoundError, \
    ApplicationImplicitPermissionError


class ExperimentService:

    def __init__(self, context: Context):
        self.context = context

    @transaction.atomic
    def create_experiment(self, *, name: str, creator: settings.AUTH_USER_MODEL, **optional) -> Experiment:
        optional.pop('created_at', None)

        experiment = Experiment(**optional)
        experiment.context = self.context
        experiment.name = name
        experiment.creator = creator

        return self._validate_and_save(experiment)

    def list_experiments(self) -> QuerySet[Experiment]:
        return Experiment.objects.filter(context=self.context)

    def list_experiments_by_creator(self, creator: settings.AUTH_USER_MODEL) -> QuerySet[Experiment]:
        return self.list_experiments().filter(creator=creator)

    def retrieve_experiment(self, name: str, creator: settings.AUTH_USER_MODEL) -> Experiment:
        try:
            return self.list_experiments_by_creator(creator).get(name=name)
        except Experiment.DoesNotExist:
            raise ApplicationNotFoundError(f'No experiment named "{name}", created by "{creator.username}", exists in '
                                           f'context "{self.context.name}"')

    @transaction.atomic
    def update_experiment(self, ref_creator: settings.AUTH_USER_MODEL, ref_name: str, **update_values):
        update_values.pop('context', None)
        update_values.pop('created_at', None)
        update_values.pop('creator', None)

        experiment = self.retrieve_experiment(ref_name, ref_creator)

        for field_name, value in update_values.items():
            experiment.__setattr__(field_name, value)

        return self._validate_and_save(experiment)

    @transaction.atomic
    def delete_experiment(self, name: str, creator: settings.AUTH_USER_MODEL):
        experiment = self.retrieve_experiment(name, creator)
        experiment.delete()

    @transaction.atomic
    def _validate_and_save(self, experiment: Experiment):
        try:
            experiment.full_clean(validate_unique=False, validate_constraints=False)
        except ValidationError as e:
            raise ApplicationValidationError(str(e)) from e

        try:
            experiment.save()
        except IntegrityError as e:
            raise ApplicationDuplicateError(str(e)) from e

        experiment.refresh_from_db()
        return experiment


class ExperimentTaskService:

    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    @transaction.atomic
    def set_tasks(self, tasks: Iterable[Task]):
        task_set = set(tasks)
        context_task_set = set(Task.objects.filter(context=self.experiment.context))
        non_context_task_set = task_set.difference(context_task_set)
        if len(non_context_task_set) > 0:
            raise ApplicationImplicitPermissionError(
                f'Task "{non_context_task_set.pop().uuid}" is not a part of the experiment\'s context'
            )
        self.experiment.tasks.set(tasks)

    def get_tasks(self) -> QuerySet[Task]:
        return self.experiment.tasks.all()
