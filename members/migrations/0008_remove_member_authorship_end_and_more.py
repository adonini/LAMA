# Generated by Django 5.0.7 on 2024-12-10 07:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0007_remove_member_secondary_email'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='authorship_end',
        ),
        migrations.RemoveField(
            model_name='member',
            name='authorship_start',
        ),
        migrations.RemoveField(
            model_name='member',
            name='end_date',
        ),
        migrations.RemoveField(
            model_name='member',
            name='institute',
        ),
        migrations.RemoveField(
            model_name='member',
            name='is_author',
        ),
        migrations.RemoveField(
            model_name='member',
            name='start_date',
        ),
        migrations.CreateModel(
            name='AuthorshipPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='authorship_periods', to='members.member')),
            ],
        ),
        migrations.CreateModel(
            name='MembershipPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('institute', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.institute')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='membership_periods', to='members.member')),
            ],
        ),
    ]
