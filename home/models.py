from django.db import models

# #
from armaan_bhai.models import AbstractTimeStamp
from user.models import User


class TotalVisit(AbstractTimeStamp):
    visitor = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Total Visit'
        verbose_name_plural = 'Total Visits'
        db_table = 'total_visits'

    def __str__(self):
        return f"{self.pk}"
