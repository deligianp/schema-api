from rest_framework import serializers

from experiments.models import Experiment


class ExperimentsListSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(source='creator.username', read_only=True)

    class Meta:
        model = Experiment
        fields = ('name', 'created_at', 'creator')
        read_only_fields = ('name', 'created_at', 'creator')


class ExperimentSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(source='creator.username', read_only=True)

    class Meta:
        model = Experiment
        fields = ('name', 'description', 'created_at', 'creator')
        read_only_fields = ('created_at',)
