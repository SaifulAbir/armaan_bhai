# Generated by Django 4.1.3 on 2023-03-02 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0012_suborder_pickup_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentpickuplocation',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]
