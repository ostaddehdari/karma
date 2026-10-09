from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspaces', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=180)),
                ('code', models.CharField(blank=True, max_length=50)),
                ('description', models.TextField(blank=True)),
                ('priority', models.PositiveSmallIntegerField(choices=[(1, 'فوری'), (2, 'خیلی بالا'), (3, 'بالا'), (4, 'عادی'), (5, 'پایین')], default=4)),
                ('manual_order', models.PositiveIntegerField(default=1000)),
                ('status', models.CharField(choices=[('planning', 'برنامه‌ریزی'), ('active', 'در حال اجرا'), ('waiting', 'در انتظار'), ('paused', 'متوقف'), ('done', 'تکمیل‌شده'), ('cancelled', 'لغوشده')], default='planning', max_length=16)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('progress_cache', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_projects', to=settings.AUTH_USER_MODEL)),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_projects', to='workspaces.workspacemember')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='workspaces.workspace')),
            ],
        ),
        migrations.CreateModel(
            name='ActivityEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('verb', models.CharField(max_length=100)),
                ('description', models.CharField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='projects.project')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Milestone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('is_done', models.BooleanField(default=False)),
                ('position', models.PositiveIntegerField(default=0)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='milestones', to='projects.project')),
            ],
        ),
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('manager', 'مدیر پروژه'), ('member', 'عضو'), ('viewer', 'مشاهده‌گر')], default='member', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='projects.project')),
                ('workspace_member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_accesses', to='workspaces.workspacemember')),
            ],
            options={'unique_together': {('project', 'workspace_member')}},
        ),
        migrations.CreateModel(
            name='TaskList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('position', models.PositiveIntegerField(default=0)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_lists', to='projects.project')),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('todo', 'برای انجام'), ('doing', 'در حال انجام'), ('review', 'بازبینی'), ('done', 'انجام‌شده'), ('blocked', 'مسدود')], default='todo', max_length=16)),
                ('priority', models.PositiveSmallIntegerField(choices=[(1, 'فوری'), (2, 'بالا'), (3, 'عادی'), (4, 'پایین')], default=3)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('progress', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assignee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tasks', to='workspaces.workspacemember')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_tasks', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='projects.project')),
                ('task_list', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='projects.tasklist')),
            ],
        ),
        migrations.CreateModel(
            name='ChecklistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('is_done', models.BooleanField(default=False)),
                ('position', models.PositiveIntegerField(default=0)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checklist', to='projects.task')),
            ],
        ),
    ]
