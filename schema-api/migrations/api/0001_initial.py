# Generated by Django 5.0.4 on 2024-07-16 14:37

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Context',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Env',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Name of the container's environment variable (e.g. PATH for $PATH)", max_length=255)),
                ('value', models.TextField(blank=True, help_text="Value of the container's environment variable")),
            ],
        ),
        migrations.CreateModel(
            name='Executor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveSmallIntegerField(help_text='Execution order of the executor')),
                ('command', models.JSONField(help_text='JSON array-definition of the command to run inside the container')),
                ('image', models.CharField(help_text='Docker image reference', max_length=255)),
                ('stderr', models.CharField(help_text='Path to a file inside the container to which to dump stderr', max_length=255)),
                ('stdin', models.CharField(help_text='Path to a file inside the container to read input from', max_length=255)),
                ('stdout', models.CharField(help_text='Path to a file inside the container to which to dump stdout', max_length=255)),
                ('workdir', models.CharField(blank=True, help_text='Path to a directory inside the container where the command will be executed', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='ExecutorOutputLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stdout', models.TextField()),
                ('stderr', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='MountPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255)),
                ('url', models.CharField(help_text='Path to the file/directory, in the implemented filesystem', max_length=255)),
                ('path', models.CharField(help_text='Path to the file/directory, in the container', max_length=255)),
                ('type', models.CharField(choices=[('FILE', 'FILE'), ('DIRECTORY', 'DIRECTORY')], max_length=10)),
                ('is_input', models.BooleanField(default=True, help_text='Whether the file is an input file and should be located and mounted to the container during initialization')),
                ('content', models.TextField(help_text='Input file content if url is not defined')),
            ],
        ),
        migrations.CreateModel(
            name='Participation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='ResourceSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpu_cores', models.IntegerField(default=1)),
                ('ram_gb', models.FloatField(default=1)),
                ('disk_gb', models.FloatField(default=5)),
                ('preemptible', models.BooleanField(null=True)),
                ('zones', models.JSONField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=255)),
                ('value', models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, help_text='A unique UUID for identifying a task on this API', unique=True)),
                ('task_id', models.CharField(db_column='api_task_id', help_text='Task ID that assigned to task by underlying API', max_length=255)),
                ('name', models.CharField(help_text='User-provided name', max_length=255)),
                ('description', models.TextField(help_text='User-provided description')),
                ('pending', models.BooleanField(default=True, help_text="A boolean field that indicates whether a task is still running; completed tasks won't poll the underlying TESK API for the task status")),
                ('status', models.CharField(choices=[('SUBMITTED', 'SUBMITTED'), ('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED'), ('SCHEDULED', 'SCHEDULED'), ('INITIALIZING', 'INITIALIZING'), ('RUNNING', 'RUNNING'), ('ERROR', 'ERROR'), ('COMPLETED', 'COMPLETED'), ('UNKNOWN', 'UNKNOWN'), ('CANCELED', 'CANCELED')], default='SUBMITTED', help_text='Task status', max_length=30)),
                ('submitted_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp of task being approved and getting created')),
                ('latest_update', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Volume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=255)),
            ],
        ),
    ]
