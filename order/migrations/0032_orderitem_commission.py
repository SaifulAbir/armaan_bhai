# Generated by Django 4.1.3 on 2023-06-05 08:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0031_alter_farmeraccountinfo_account_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='commission',
            field=models.FloatField(default=0, help_text='Agent Commission', max_length=255),
        ),
    ]