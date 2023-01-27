I've been spending a non trivial amount of time going through some investigation and trial-and-error attempts to come up with a way to have my Django model define a `CharField` with choices taken from a settings value, and avoid migrations being generated every time the settings change.

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
    tag = models.CharField(max_length=2, choices=Tag.choices)
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

After reading the Stackoverflow posts and their linked bugs, I concluded that (in theory) this issue would be workaround-able by [passing a callable to choices](https://code.djangoproject.com/ticket/22837#comment:4). This approach made total sense to me and I went happily and quickly to create a PR with this change:

```diff
--- a/choices-no-migrations/example/expenses/models.py
+++ b/choices-no-migrations/example/expenses/models.py
@@ -13,4 +13,4 @@ class Expense(models.Model):
     what = models.TextField()
     when = models.DateTimeField(default=now)
     amount = models.DecimalField(decimal_places=2, max_digits=20)
-    tag = models.CharField(max_length=2, choices=Tag.choices)
+    tag = models.CharField(max_length=2, choices=lambda: Tag.choices)
```

then I ran the tests to ensure things worked as expected, but...

```
ERRORS:
expenses.Expense.tag: (fields.E004) 'choices' must be an iterable (e.g., a list or tuple).
```

Naturally, I searched for the documentation to check how the callable should be passed to the `choices` param (at the time of this writing, the doc is [this one](https://docs.djangoproject.com/en/4.1/ref/models/fields/#django.db.models.Field.choices)), and to my surprise there was no mention of allowing a callable at all.

Some more googling and I came across [this other post](https://stackoverflow.com/questions/33514058/django-creates-pointless-migrations-on-choices-list-change/33514551#33514551), where the most voted response says *I think you're mixing up the `choices` argument on a `Model` field, and that on a `forms.ChoiceField` field.*

Eureka! I was (also) indeed mixing up the two fields: not in my head, but my searches weren't specific enough, and the search results were sort of also mixing those two up. So back to square zero where I need my tag list to be taken from a settings value and ideally not having new migrations generated when that settings change.

I tried a few things that did not work out, until a colleague suggested that I may need to edit the latest migration to replace the explicit tag list with the variable definition, and this way the "migration system" would be happy enough that `Tag.choices` is not changing thus not producing a new migration on tags change. So:

```diff
--- a/choices-no-migrations/example/expenses/migrations/0001_initial.py
+++ b/choices-no-migrations/example/expenses/migrations/0001_initial.py
@@ -3,6 +3,8 @@
 from django.db import migrations, models
 import django.utils.timezone

+from expenses.models import Expense
+

 class Migration(migrations.Migration):

@@ -35,12 +37,7 @@ class Migration(migrations.Migration):
                 (
                     'tag',
                     models.CharField(
-                        choices=[
-                            ('FD', 'Food'),
-                            ('HS', 'Housing'),
-                            ('TR', 'Transportation'),
-                            ('UT', 'Utilities'),
-                        ],
+                        choices=Expense.Tag.choices,
                         max_length=2,
                     ),
                 ),
```

would successfully allow for my use case! After this change, adding to or removing from the tag list and then running `makemigrations` would not detect any changes:

```bash
$ python manage.py makemigrations
No changes detected
```

It's worth noting that after I completed my solution, and when I started writing this post, I've found a [similar writing from 2017](http://tech.yunojuno.com/pro-tip-django-choices-and-migrations) which proposes an analogue solution, but I figured this post was worth writing anyways since I spent hours banging my head against the desk until I solved it.