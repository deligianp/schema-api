from django.db import models

from api.models import Context, Participation


class Quotas(models.Model):
    max_active_disk_gb = models.PositiveSmallIntegerField(null=True)
    max_active_ram_gb = models.PositiveSmallIntegerField(null=True)
    max_active_cpu_cores = models.PositiveSmallIntegerField(null=True)
    max_ram_gb_request = models.PositiveSmallIntegerField(null=True)
    max_disk_gb_request = models.PositiveSmallIntegerField(null=True)
    max_cpu_cores_request = models.PositiveSmallIntegerField(null=True)
    max_active_tasks = models.PositiveSmallIntegerField(null=True)
    total_tasks = models.PositiveIntegerField(null=True)
    max_executors_request = models.PositiveSmallIntegerField(null=True)


class ContextQuotas(Quotas):
    context = models.OneToOneField(Context, on_delete=models.CASCADE, related_name='quotas')


class ParticipationQuotas(Quotas):
    participation = models.OneToOneField(Participation, on_delete=models.CASCADE, related_name='quotas')
