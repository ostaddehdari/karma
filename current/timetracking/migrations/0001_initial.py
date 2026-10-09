# Generated for KARMA 1.5.0
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspaces', '0001_initial'),
        ('projects', '0003_task_completed_at_project_progress_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_type', models.CharField(choices=[('manual', 'ثبت دستی'), ('timer', 'تایمر')], default='manual', max_length=12)),
                ('started_at', models.DateTimeField()),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('duration_seconds', models.PositiveIntegerField(default=0)),
                ('note', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_work_logs', to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='work_logs', to='workspaces.workspacemember')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_logs', to='projects.project')),
                ('task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='work_logs', to='projects.task')),
            ],
            options={'ordering': ['-started_at', '-id']},
        ),
        migrations.AddIndex(
            model_name='worklog',
            index=models.Index(fields=['project', 'started_at'], name='worklog_proj_started_idx'),
        ),
        migrations.AddIndex(
            model_name='worklog',
            index=models.Index(fields=['member', 'started_at'], name='worklog_member_started_idx'),
        ),
    ]
