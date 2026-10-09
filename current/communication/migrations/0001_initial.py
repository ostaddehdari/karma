from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('follow_up', 'پیگیری'), ('documents', 'مستندات'), ('custom', 'گروه'), ('private', 'خصوصی')], max_length=20)),
                ('title', models.CharField(max_length=160)),
                ('token', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='projects.project')),
            ],
            options={'unique_together': {('project', 'kind', 'title')}},
        ),
        migrations.CreateModel(
            name='ConversationParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='communication.conversation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversation_participations', to=settings.AUTH_USER_MODEL)),
            ],
            options={'unique_together': {('conversation', 'user')}},
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited_at', models.DateTimeField(blank=True, null=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='communication.conversation')),
                ('reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='communication.message')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='MessageAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='chat/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('media_type', models.CharField(choices=[('image', 'تصویر'), ('video', 'ویدئو'), ('audio', 'صوت'), ('document', 'سند'), ('other', 'فایل')], default='other', max_length=20)),
                ('is_voice_recording', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='communication.message')),
            ],
        ),
        migrations.CreateModel(
            name='ProjectDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('file', models.FileField(blank=True, null=True, upload_to='documents/%Y/%m/')),
                ('text_content', models.TextField(blank=True)),
                ('media_type', models.CharField(choices=[('text', 'متن'), ('image', 'تصویر'), ('video', 'ویدئو'), ('audio', 'صوت'), ('document', 'سند'), ('other', 'فایل')], default='document', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='projects.project')),
                ('source_message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mirrored_documents', to='communication.message')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Letter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('internal', 'داخلی'), ('incoming', 'وارده'), ('outgoing', 'صادره')], default='internal', max_length=16)),
                ('number', models.CharField(blank=True, max_length=64)),
                ('subject', models.CharField(max_length=220)),
                ('body', models.TextField()),
                ('sender_name', models.CharField(blank=True, max_length=160)),
                ('recipient_name', models.CharField(blank=True, max_length=160)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='letters/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_letters', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='letters', to='projects.project')),
            ],
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('body', models.TextField(blank=True)),
                ('color', models.CharField(default='#FFF6BF', max_length=12)),
                ('is_pinned', models.BooleanField(default=False)),
                ('is_archived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='private_notes', to='projects.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='NoteChecklistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('is_done', models.BooleanField(default=False)),
                ('note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checklist', to='communication.note')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('body', models.CharField(blank=True, max_length=500)),
                ('url', models.CharField(blank=True, max_length=500)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
