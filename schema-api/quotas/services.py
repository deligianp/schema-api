import logging
from typing import Iterable

from django.db import transaction

from api.models import Participation, Context
from api_auth.models import AuthEntity
from quotas.models import Quotas, ContextQuotas, ParticipationQuotas
from util.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class QuotasService:

    def __init__(self, context: Context, user: AuthEntity = None):
        self.context = context
        self.user = user
        if user is not None:
            try:
                self.participation = Participation.objects.get(context=context, user=user)
            except Participation.DoesNotExist:
                raise ApplicationNotFoundError(
                    f'User "{self.user.username}" does not participate in context "{self.context.name}".')

    def _get_context_quotas(self) -> ContextQuotas:
        try:
            logging.debug('Attempting to find existing quotas for context')
            quotas = self.context.quotas
            logging.debug('Existing quotas found')
        except ContextQuotas.DoesNotExist:
            logging.debug('No existing quotas were found')
            logging.debug('Setting quotas as empty context quotas')
            quotas = ContextQuotas()
        return quotas

    def _get_participation_quotas(self) -> ParticipationQuotas:
        try:
            logging.debug('Attempting to find existing quotas for participation')
            quotas = self.participation.quotas
            logging.debug('Existing quotas found')
        except ParticipationQuotas.DoesNotExist:
            logging.debug('No existing quotas were found')
            logging.debug('Setting quotas as empty participation quotas')
            quotas = ParticipationQuotas()
        return quotas

    def get_quotas(self) -> Quotas:
        if self.user is not None:
            return self._get_participation_quotas()
        return self._get_context_quotas()

    def get_qualified_quotas(self) -> Iterable[Quotas]:
        related_quotas = list()
        related_quotas.append(self._get_context_quotas())
        if self.user is not None:
            related_quotas.append(self._get_participation_quotas())
        return related_quotas

    @transaction.atomic
    def set_quotas(self, **quotas) -> Quotas:
        logging.debug('Retrieving quotas')
        quotas_obj = self.get_quotas()
        logging.debug('Overwriting quotas with provided values')
        for q, v in quotas.items():
            setattr(quotas_obj, q, v)
        logging.debug('Assuring quotas object is related to the corresponding object')
        if self.user is not None:
            quotas_obj.participation = Participation.objects.get(context=self.context, user=self.user)
        else:
            quotas_obj.context = self.context
        logging.debug('Saving quotas')
        quotas_obj.save()
        logging.debug('Returning persisted quotas')
        return quotas_obj

    @transaction.atomic
    def unset_quotas(self) -> None:
        if self.user is not None:
            try:
                quotas = ParticipationQuotas.objects.get(participation__context=self.context,
                                                         participation__user=self.user)
                quotas.delete()
            except ParticipationQuotas.DoesNotExist:
                pass
        else:
            try:
                quotas = self.context.quotas
                quotas.delete()
            except ContextQuotas.DoesNotExist:
                pass
