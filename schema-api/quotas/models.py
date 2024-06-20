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

    def unset(self):
        self.max_active_disk_gb = None
        self.max_active_ram_gb = None
        self.max_active_cpu_cores = None
        self.max_ram_gb_request = None
        self.max_disk_gb_request = None
        self.max_cpu_cores_request = None
        self.max_active_tasks = None
        self.total_tasks = None
        self.max_executors_request = None


class ContextQuotas(Quotas):
    context = models.OneToOneField(Context, on_delete=models.CASCADE, related_name='quotas')


class ParticipationQuotas(Quotas):
    participation = models.OneToOneField(Participation, on_delete=models.CASCADE, related_name='quotas')
