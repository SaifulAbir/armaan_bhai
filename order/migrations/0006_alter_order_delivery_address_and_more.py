# Generated by Django 4.1.3 on 2023-02-08 04:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0005_order_is_qc_passed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='delivery_address',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='order.deliveryaddress'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='product_count',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
