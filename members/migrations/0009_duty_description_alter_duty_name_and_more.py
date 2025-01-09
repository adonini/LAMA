# Generated by Django 5.0.7 on 2024-12-10 08:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0008_remove_member_authorship_end_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='duty',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='duty',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='memberduty',
            name='duty',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='members.duty'),
        ),
        migrations.AlterUniqueTogether(
            name='memberduty',
            unique_together={('member', 'duty', 'start_date')},
        ),
    ]
