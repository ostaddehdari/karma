from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_profile_phone_normalized_and_updated_at')]
    operations = [
        migrations.AlterField(
            model_name='profile',
            name='phone_normalized',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
