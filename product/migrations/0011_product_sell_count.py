# Generated by Django 4.1.3 on 2023-02-08 04:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0010_product_possible_delivery_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='sell_count',
            field=models.IntegerField(default=0),
        ),
    ]