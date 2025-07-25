# Generated by Django 5.0.4 on 2024-09-04 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_remove_task_name_not_empty_remove_task_status_enum_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TempTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=255)),
                ('tasks', models.ManyToManyField(related_name='temptags', to='api.task')),
            ],
        ),
        migrations.AddConstraint(
            model_name='temptag',
            constraint=models.UniqueConstraint(fields=('value',), name='tag_value_unique'),
        ),
        migrations.AddConstraint(
            model_name='temptag',
            constraint=models.CheckConstraint(check=models.Q(('value__regex', '^\\s*$'), _negated=True), name='tag_value_not_empty'),
        ),
    ]
