from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0033_duty_grants_authorship_without_cf'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='duty',
            name='grants_authorship_without_cf',
        ),
    ]
