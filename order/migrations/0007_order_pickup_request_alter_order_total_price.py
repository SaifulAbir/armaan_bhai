# Generated by Django 4.1.3 on 2023-02-12 11:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0006_alter_order_delivery_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='pickup_request',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_price',
            field=models.DecimalField(decimal_places=2, max_digits=19),
        ),
    ]
