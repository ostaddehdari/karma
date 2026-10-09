from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Notebook = apps.get_model('communication', 'Notebook')
    NoteSection = apps.get_model('communication', 'NoteSection')
    Note = apps.get_model('communication', 'Note')
    for user in User.objects.iterator():
        notebook = Notebook.objects.filter(user=user, is_archived=False).order_by('position', 'created_at').first()
        if notebook is None:
            notebook = Notebook.objects.create(user=user, title='دفترچه من', color='#6759E7')
        section = NoteSection.objects.filter(notebook=notebook).order_by('position', 'created_at').first()
        if section is None:
            section = NoteSection.objects.create(notebook=notebook, title='یادداشت‌ها', position=1)
        Note.objects.filter(user=user, notebook__isnull=True).update(notebook=notebook, section=section)


class Migration(migrations.Migration):
    dependencies = [('communication', '0003_alter_letter_attachment_alter_messageattachment_file_and_more')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
