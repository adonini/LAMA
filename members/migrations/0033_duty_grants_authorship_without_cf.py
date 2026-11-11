from django.db import migrations, models
from django.db.models import Q


def mark_emeritus_duties(apps, schema_editor):
    Duty = apps.get_model('members', 'Duty')
    Duty.objects.filter(
        Q(name__iexact='Emeritus') | Q(name__iexact='Emeritus status')
    ).update(
        grants_authorship_without_cf=True,
    )


def unmark_emeritus_duties(apps, schema_editor):
    Duty = apps.get_model('members', 'Duty')
    Duty.objects.filter(
        Q(name__iexact='Emeritus') | Q(name__iexact='Emeritus status')
    ).update(
        grants_authorship_without_cf=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0032_digestreportstate_alter_authordetails_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='duty',
            name='grants_authorship_without_cf',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Grant authorship for the assignment period without '
                    'requiring Common Fund status.'
                ),
            ),
        ),
        migrations.RunPython(mark_emeritus_duties, unmark_emeritus_duties),
    ]
