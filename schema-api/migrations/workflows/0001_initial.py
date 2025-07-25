# Generated by Django 5.1.7 on 2025-06-22 20:08

import django.db.models.deletion
import util.defaults
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0011_remove_statushistorypoint_status_history_enum_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, help_text='UUID reference to a schedulable', unique=True)),
                ('backend_ref', models.CharField(help_text='Backend reference ID assigned to a scheduled execution by underlying execution API', max_length=255)),
                ('manager_name', models.CharField(help_text='Manager name handling the execution', max_length=255)),
                ('name', models.CharField(blank=True, help_text='User-provided name', max_length=255)),
                ('description', models.TextField(blank=True, help_text='User-provided description')),
                ('execution_order', models.CharField(blank=True, max_length=255)),
                ('submitted_at', models.DateTimeField(default=util.defaults.get_current_datetime)),
                ('context', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.context')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(choices=[('SNWL', 'Snwl')], max_length=32)),
                ('version', models.CharField(blank=True, max_length=16)),
                ('content', models.TextField(blank=True)),
                ('workflow', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='specification', to='workflows.workflow')),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowExecutor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command', models.JSONField(help_text='JSON array-definition of the command to run inside the container')),
                ('image', models.CharField(help_text='Docker image reference', max_length=255)),
                ('stderr', models.CharField(blank=True, help_text='Path to a file inside the container to which to dump stderr', max_length=255)),
                ('stdin', models.CharField(blank=True, help_text='Path to a file inside the container to read input from', max_length=255)),
                ('stdout', models.CharField(blank=True, help_text='Path to a file inside the container to which to dump stdout', max_length=255)),
                ('workdir', models.CharField(blank=True, help_text='Path to a directory inside the container where the command will be executed', max_length=255)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executors', to='workflows.workflow')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowEnv',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Name of the container's environment variable (e.g. PATH for $PATH)", max_length=255)),
                ('value', models.TextField(blank=True, help_text="Value of the container's environment variable")),
                ('executor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='env', to='workflows.workflowexecutor')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowExecutorOutputLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stdout', models.JSONField(default=list)),
                ('stderr', models.JSONField(default=list)),
                ('executor', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='workflows.workflowexecutor')),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowExecutorYield',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('path', models.CharField(max_length=255)),
                ('executor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='yields', to='workflows.workflowexecutor')),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowInputMountPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('type', models.CharField(choices=[('FILE', 'FILE'), ('DIRECTORY', 'DIRECTORY')], max_length=10)),
                ('url', models.CharField(blank=True, max_length=255)),
                ('content', models.TextField(blank=True, help_text='Input file content if url is not defined')),
                ('name', models.CharField(max_length=255)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inputs', to='workflows.workflow')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowOutputMountPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('url', models.CharField(help_text='Path to the file/directory, in the implemented filesystem', max_length=255)),
                ('type', models.CharField(choices=[('FILE', 'FILE'), ('DIRECTORY', 'DIRECTORY')], max_length=10)),
                ('name', models.CharField(max_length=255)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outputs', to='workflows.workflow')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowResourceSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpu_cores', models.IntegerField(default=1)),
                ('ram_gb', models.FloatField(default=1)),
                ('disk_gb', models.FloatField(default=5)),
                ('preemptible', models.BooleanField(null=True)),
                ('zones', models.JSONField(null=True)),
                ('workflow', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='resources', to='workflows.workflow')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowStatusLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(choices=[(-1, 'UNKNOWN'), (0, 'SUBMITTED'), (1, 'APPROVED'), (2, 'REJECTED'), (3, 'QUEUED'), (4, 'SCHEDULED'), (5, 'INITIALIZING'), (6, 'RUNNING'), (7, 'COMPLETED'), (8, 'ERROR'), (9, 'CANCELED')])),
                ('created_at', models.DateTimeField(default=util.defaults.get_current_datetime)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_logs', to='workflows.workflow')),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=255)),
                ('workflow', models.ManyToManyField(related_name='tags', to='workflows.workflow')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
