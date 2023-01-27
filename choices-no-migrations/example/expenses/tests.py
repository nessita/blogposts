from django.test import TestCase

from expenses.models import Expense


class ExpenseTestCase(TestCase):
    def test_tags(self):
        expense = Expense.objects.create(amount='10.23', tag=Expense.Tag.FOOD)

        self.assertEqual(expense.tag, Expense.Tag.FOOD)
