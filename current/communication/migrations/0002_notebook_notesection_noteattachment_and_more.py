from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('communication', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notebook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160)),
                ('color', models.CharField(default='#6759E7', max_length=12)),
                ('icon', models.CharField(default='fa-book', max_length=40)),
                ('position', models.PositiveIntegerField(default=0)),
                ('is_archived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notebooks', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['position', 'created_at']},
        ),
        migrations.CreateModel(
            name='NoteSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160)),
                ('position', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notebook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='communication.notebook')),
            ],
            options={'ordering': ['position', 'created_at']},
        ),
        migrations.AddField(
            model_name='note',
            name='notebook',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notes', to='communication.notebook'),
        ),
        migrations.AddField(
            model_name='note',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notes', to='communication.notesection'),
        ),
        migrations.AlterField(
            model_name='note',
            name='color',
            field=models.CharField(default='#FFFFFF', max_length=12),
        ),
        migrations.AddField(
            model_name='notechecklistitem',
            name='position',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='NoteAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='notes/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('media_type', models.CharField(choices=[('image', 'تصویر'), ('video', 'ویدئو'), ('audio', 'صوت'), ('document', 'سند'), ('other', 'فایل')], default='other', max_length=20)),
                ('caption', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='communication.note')),
            ],
        ),
    ]
