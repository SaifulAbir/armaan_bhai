# Generated by Django 4.1.3 on 2022-11-27 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_agentfarmer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='terms_and_conditions',
            field=models.BooleanField(default=False),
        ),
    ]