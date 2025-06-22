from django.db import models


class WorkflowLanguages(models.TextChoices):
    # Supported workflow language names should go here

    SNWL = 'SNWL'
