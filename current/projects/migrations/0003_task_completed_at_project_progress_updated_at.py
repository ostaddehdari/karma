from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0002_project_is_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='progress_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
