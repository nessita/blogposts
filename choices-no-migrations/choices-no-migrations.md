I've been spending a few hours going through some investigation and trial-and-error to come up with a way to have my Django model define a `CharField` with choices taken from a settings value, and avoid migrations being generated every time the settings change.

Since this task proved to be more challenging than what I anticipated, I decided to write my first blogpost ever.

Before jumping into the juicy details, let's propose a simple example for an expense tracking Django app, where an `Expense` model is defined, similar to this one (simplified version!):

```python
from django.db import models
from django.utils.timezone import now


class Expense(models.Model):
    class Tag(models.TextChoices):
        FOOD = 'FD'
        HOUSING = 'HS'
        TRANSPORTATION = 'TR'
        UTILITIES = 'UT'

    what = models.TextField()
    when = models.DateTimeField(default=now)
    amount = models.DecimalField(decimal_places=2, max_digits=20)
    tag = models.CharField(max_length=2,choices=Tag.choices)
```

with it corresponding initial migration:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('what', models.TextField()),
                (
                    'when', models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    'amount',
                    models.DecimalField(decimal_places=2, max_digits=20),
                ),
                (
                    'tag',
                    models.CharField(
                        choices=[
                            ('FD', 'Food'),
                            ('HS', 'Housing'),
                            ('TR', 'Transportation'),
                            ('UT', 'Utilities'),
                        ],
                        max_length=2,
                    ),
                ),
            ],
        ),
    ]
```

Every time we change the definition of Tags, a new migration is generated. For example, suppose we add a new tag for `clothing`:

```diff
--- a/choices-no-migrations/example/expenses/models.py
+++ b/choices-no-migrations/example/expenses/models.py
@@ -3,12 +3,13 @@ from django.db import models

 class Expense(models.Model):
     class Tag(models.TextChoices):
+        CLOTHING = 'CL'
         FOOD = 'FD'
         HOUSING = 'HS'
         TRANSPORTATION = 'TR'
```

running `makemigrations` would generate a new one that looks like this:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='tag',
            field=models.CharField(
                choices=[
                    ('CL', 'Clothing'),
                    ('FD', 'Food'),
                    ('HS', 'Housing'),
                    ('TR', 'Transportation'),
                    ('UT', 'Utilities'),
                ],
                max_length=2,
            ),
        ),
    ]
```

According to a many Stackoverflow reports (for example [this one](https://stackoverflow.com/questions/46945013/django-migrations-changing-choices-value), or [this one](https://stackoverflow.com/questions/30630121/django-charfield-choices-and-migration), or even [this one](https://stackoverflow.com/questions/31788450/stop-django-from-creating-migrations-if-the-list-of-choices-of-a-field-changes)) which reference various Django bugs (ultimately pointing to [bug 22837](https://code.djangoproject.com/ticket/22837), this behavior is by design.

In most cases this is not an issue at all, but I've found it particularly annoying when my project:

 1. uses a 3rd party app that defines values that I use as choices for my model field, and that list of values changes, or 
 2. allows for customization of a list of choices by using a settings value.

Concretely, my pet project for expense tracking uses [django_countries](https://pypi.org/project/django-countries/). This library is used to associate expense entries with the country they were originated from. Every time I update my project dependencies, it's likely that a new version of `django_countries` would generate a new migration for my app because a small fix in a country name or similar.

So, given the above, and following the expense tag example from above (where the list of tag choices is very likely to be customized by each setup of the expense tracking system), I started investigating how to allow for tag list customization via settings without generating migrations every time that tag list changes.

After reading the Stackoverflow posts and their linked bugs, I concluded that (in theory) this issue would be workaround-able by [passing a callable to choices](https://code.djangoproject.com/ticket/22837#comment:4). This approach made total sense to me and I went happily and quickly to create a PR with this change.


