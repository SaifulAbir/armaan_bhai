# Generated by Django 4.1.3 on 2022-11-28 06:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_otpmodel_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otpmodel',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_otp', to=settings.AUTH_USER_MODEL),
        ),
    ]