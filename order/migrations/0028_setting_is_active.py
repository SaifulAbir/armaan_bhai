# Generated by Django 4.1.3 on 2023-05-03 08:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0027_setting_delivery_charge'),
    ]

    operations = [
        migrations.AddField(
            model_name='setting',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
