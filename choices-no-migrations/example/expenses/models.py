from django.db import models
from django.utils.timezone import now


class Tag(models.TextChoices):
    CLOTHING = 'CL'
    FOOD = 'FD'
    HOUSING = 'HS'
    TRANSPORTATION = 'TR'
    UTILITIES = 'UT'


class Expense(models.Model):
    what = models.TextField()
    when = models.DateTimeField(default=now)
    amount = models.DecimalField(decimal_places=2, max_digits=20)
    tag = models.CharField(max_length=2, choices=Tag.choices)
