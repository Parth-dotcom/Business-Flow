
from calendar import monthrange
from datetime import date

from django.db import transaction
from django.utils import timezone

from .models import Expense


def add_months(original_date, months):
    month_index = original_date.month - 1 + months
    year = original_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(original_date.day, monthrange(year, month)[1])

    return date(year, month, day)


def recurring_period_for(expense_date, frequency):
    if frequency == "MONTHLY":
        return expense_date.strftime("%Y-%m")

    if frequency == "YEARLY":
        return expense_date.strftime("%Y")

    return ""


def generate_recurring_expenses(until_date=None):
    until_date = until_date or timezone.localdate()
    created_count = 0

    with transaction.atomic():
        parents = Expense.objects.filter(
            recurring_parent__isnull=True,
            frequency__in=["MONTHLY", "YEARLY"],
            expense_date__lte=until_date,
        )

        for parent in parents:
            skipped_periods = set(
                parent.recurring_skipped_periods or []
            )

            current_date = parent.expense_date

            while current_date <= until_date:
                if (
                    parent.recurring_end_date
                    and current_date > parent.recurring_end_date
                ):
                    break

                if current_date > parent.expense_date:
                    period = recurring_period_for(
                        current_date,
                        parent.frequency,
                    )

                    if period not in skipped_periods:
                        already_exists = Expense.objects.filter(
                            recurring_parent=parent,
                            recurring_period=period,
                        ).exists()

                        if not already_exists:
                            Expense.objects.create(
                                title=parent.title,
                                category=parent.category,
                                description=parent.description,
                                amount=parent.amount,
                                expense_date=current_date,
                                frequency="ONCE",
                                recurring_parent=parent,
                                recurring_period=period,
                                created_by=parent.created_by,
                            )

                            created_count += 1

                if parent.frequency == "MONTHLY":
                    current_date = add_months(current_date, 1)
                else:
                    try:
                        current_date = current_date.replace(
                            year=current_date.year + 1
                        )
                    except ValueError:
                        current_date = current_date.replace(
                            year=current_date.year + 1,
                            day=28,
                        )

    return created_count
