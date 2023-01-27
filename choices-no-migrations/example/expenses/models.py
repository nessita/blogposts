from django.db import models


class Expense(models.Model):
    class Tag(models.TextChoices):
        FOOD = 'FD'
        HOUSING = 'HS'
        TRANSPORTATION = 'TR'
        UTILITIES = 'UT'

    tag = models.CharField(
        max_length=2,
        choices=Tag.choices,
    )
