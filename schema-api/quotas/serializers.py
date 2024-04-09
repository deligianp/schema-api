from rest_framework.serializers import ModelSerializer

from quotas.models import ContextQuotas, ParticipationQuotas, Quotas


class QuotasSerializer(ModelSerializer):
    class Meta:
        model = Quotas
        exclude = ['id']


class ContextQuotasSerializer(ModelSerializer):
    class Meta:
        model = ContextQuotas
        exclude = ['id', 'context']


class ParticipationQuotasSerializer(ModelSerializer):
    class Meta:
        model = ParticipationQuotas
        exclude = ['id', 'participation']
