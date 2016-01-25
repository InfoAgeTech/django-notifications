# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-25 18:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='action',
            field=models.CharField(choices=[('ADDED', 'Added'), ('COMMENTED', 'Commented'), ('CREATED', 'Created'), ('DELETED', 'Deleted'), ('UPDATED', 'Updated'), ('UPLOADED', 'Uploaded')], max_length=20),
        ),
    ]
