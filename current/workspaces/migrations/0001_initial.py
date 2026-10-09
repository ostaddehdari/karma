from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Workspace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=140)),
                ('description', models.TextField(blank=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='workspace_logos/%Y/%m/')),
                ('color', models.CharField(default='#5B5BD6', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_archived', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_workspaces', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WorkspaceMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('phone', models.CharField(max_length=20)),
                ('role', models.CharField(choices=[('owner', 'مالک'), ('admin', 'مدیر'), ('member', 'عضو'), ('viewer', 'مشاهده‌گر')], default='member', max_length=16)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workspace_memberships', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='workspaces.workspace')),
            ],
            options={'unique_together': {('workspace', 'phone')}},
        ),
    ]
