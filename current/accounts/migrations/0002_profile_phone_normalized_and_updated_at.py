from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='profile',
            name='phone_normalized',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
