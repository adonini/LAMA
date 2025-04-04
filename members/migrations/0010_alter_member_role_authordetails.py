# Generated by Django 5.0.7 on 2025-01-09 20:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0009_duty_description_alter_duty_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='role',
            field=models.CharField(choices=[('student', 'Student'), ('technician', 'Technician'), ('researcher', 'Researcher'), ('affiliated', 'Affiliated'), ('engineer', 'Engineer'), ('administrator', 'Administrator')], max_length=20),
        ),
        migrations.CreateModel(
            name='AuthorDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_name', models.CharField(blank=True, max_length=150)),
                ('author_first_name', models.CharField(blank=True, max_length=50)),
                ('author_last_name', models.CharField(blank=True, max_length=50)),
                ('long_institute_1', models.CharField(blank=True, max_length=150)),
                ('long_institute_2', models.CharField(blank=True, max_length=150)),
                ('long_institute_3', models.CharField(blank=True, max_length=150)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('orcid', models.CharField(blank=True, max_length=19)),
                ('institute_1', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='authors_institute_1', to='members.institute')),
                ('institute_2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='authors_institute_2', to='members.institute')),
                ('institute_3', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='authors_institute_3', to='members.institute')),
                ('member', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='author_details', to='members.member')),
            ],
        ),
    ]
