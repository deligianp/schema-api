# Generated by Django 5.0.4 on 2024-07-25 06:05

import django.db.models.deletion
import util.defaults
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StatusHistoryPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=util.defaults.get_current_datetime)),
                ('status', models.IntegerField(choices=[(-1, 'UNKNOWN'), (0, 'SUBMITTED'), (1, 'APPROVED'), (2, 'REJECTED'), (3, 'SCHEDULED'), (4, 'INITIALIZING'), (5, 'RUNNING'), (6, 'COMPLETED'), (7, 'ERROR'), (8, 'CANCELED')])),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.task')),
            ],
        ),
        migrations.AddConstraint(
            model_name='statushistorypoint',
            constraint=models.CheckConstraint(check=models.Q(('status__in', [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8])), name='status_history_enum'),
        ),
        migrations.AlterUniqueTogether(
            name='statushistorypoint',
            unique_together={('task', 'status')},
        ),
    ]
