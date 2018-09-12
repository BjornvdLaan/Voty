# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-09-11 06:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('initproc', '0030_auto_20180828_1913'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='policy',
            options={'permissions': [('policy_create', 'Can create new policy'), ('policy_edit', 'Can edit policy'), ('policy_delete', 'Can delete policy'), ('policy_submit', 'Can submit policy'), ('policy_invite', 'Can invite others to co-initiate/support'), ('policy_stage', 'Can stage a policy'), ('policy_validate', 'Can validate a policy'), ('policy_invalidate', 'Can invalidate a policy'), ('policy_finalise', 'Can finalise a policy')]},
        ),
        migrations.AlterField(
            model_name='moderation',
            name='vote',
            field=models.CharField(choices=[('n', 'Reject Policy proposal'), ('y', 'Accept Policy proposal'), ('r', 'Request Improvements')], max_length=1),
        ),
        migrations.AlterField(
            model_name='policy',
            name='state',
            field=models.CharField(choices=[('draft', 'in preparation'), ('deleted', 'deleted'), ('staged', 'staged'), ('submitted', 'submitted'), ('invalidated', 'invalidated'), ('rejected', 'rejected'), ('closed', 'closed'), ('hidden', 'hidden'), ('challenged', 'challenged'), ('validated', 'validated'), ('supported', 'supported'), ('finalised', 'finalised')], default='draft', max_length=20),
        ),
    ]
