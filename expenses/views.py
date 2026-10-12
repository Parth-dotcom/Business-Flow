
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Expense
from .services import generate_recurring_expenses


ZERO = Decimal("0.00")


def parse_expense_form(request):
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "Other").strip()
    description = request.POST.get("description", "").strip()
    amount_text = request.POST.get("amount", "").strip()
    expense_date_text = request.POST.get("expense_date", "").strip()
    frequency = request.POST.get("frequency", "ONCE").strip()
    end_date_text = request.POST.get("recurring_end_date", "").strip()

    errors = []

    if not title:
        errors.append("Expense title is required.")

    valid_categories = {
        value for value, label in Expense.CATEGORY_CHOICES
    }

    if category not in valid_categories:
        errors.append("Please select a valid expense category.")

    valid_frequencies = {
        value for value, label in Expense.FREQUENCY_CHOICES
    }

    if frequency not in valid_frequencies:
        errors.append("Please select a valid expense frequency.")

    try:
        amount = Decimal(amount_text)

        if not amount.is_finite() or amount <= 0:
            errors.append("Amount must be greater than zero.")

    except (InvalidOperation, TypeError, ValueError):
        amount = None
        errors.append("Please enter a valid amount.")

    try:
        parsed_date = date.fromisoformat(expense_date_text)

    except (TypeError, ValueError):
        parsed_date = None
        errors.append("Please enter a valid expense date.")

    parsed_end_date = None

    if end_date_text:
        try:
            parsed_end_date = date.fromisoformat(end_date_text)

        except (TypeError, ValueError):
            errors.append("Please enter a valid recurring end date.")

    if (
        parsed_date
        and parsed_end_date
        and parsed_end_date < parsed_date
    ):
        errors.append(
            "Recurring end date cannot be before the expense start date."
        )

    if frequency == "ONCE" and end_date_text:
        errors.append(
            "An end date is only applicable to recurring expenses."
        )

    form_data = {
        "title": title,
        "category": category,
        "description": description,
        "amount": amount,
        "expense_date": parsed_date,
        "frequency": frequency,
        "recurring_end_date": (
            parsed_end_date if frequency != "ONCE" else None
        ),
    }

    return form_data, errors


def expense_form_context(expense, form_data, page_title):
    return {
        "expense": expense,
        "category_choices": Expense.CATEGORY_CHOICES,
        "frequency_choices": Expense.FREQUENCY_CHOICES,
        "form_data": form_data,
        "page_title": page_title,
    }


@login_required
def expense_list(request):
    generate_recurring_expenses()

    expenses = Expense.objects.all()

    category = request.GET.get("category", "").strip()
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    if category:
        expenses = expenses.filter(category=category)

    if start_date:
        expenses = expenses.filter(expense_date__gte=start_date)

    if end_date:
        expenses = expenses.filter(expense_date__lte=end_date)

    total_expenses = (
        expenses.aggregate(total=Sum("amount"))["total"] or ZERO
    )

    today = timezone.localdate()

    monthly_expenses = (
        Expense.objects.filter(
            expense_date__year=today.year,
            expense_date__month=today.month,
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    context = {
        "expenses": expenses,
        "total_expenses": total_expenses,
        "monthly_expenses": monthly_expenses,
        "category_choices": Expense.CATEGORY_CHOICES,
        "selected_category": category,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(
        request,
        "expenses/expense_list.html",
        context,
    )


@login_required
def expense_create(request):
    if request.method == "POST":
        form_data, errors = parse_expense_form(request)

        if errors:
            for error in errors:
                messages.error(request, error)

            return render(
                request,
                "expenses/expense_form.html",
                expense_form_context(
                    None,
                    request.POST,
                    "Add Expense",
                ),
            )

        with transaction.atomic():
            Expense.objects.create(
                **form_data,
                created_by=request.user,
            )

            generate_recurring_expenses()

        messages.success(
            request,
            "Expense added successfully. Recurring entries were generated "
            "where applicable.",
        )

        return redirect("expenses:expense_list")

    return render(
        request,
        "expenses/expense_form.html",
        expense_form_context(None, {}, "Add Expense"),
    )


@login_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == "POST":
        form_data, errors = parse_expense_form(request)

        if errors:
            for error in errors:
                messages.error(request, error)

            return render(
                request,
                "expenses/expense_form.html",
                expense_form_context(
                    expense,
                    request.POST,
                    "Edit Expense",
                ),
            )

        if expense.recurring_parent_id:
            messages.error(
                request,
                "This is a generated recurring entry. Edit the original "
                "recurring expense to change future entries.",
            )
            return redirect("expenses:expense_list")

        with transaction.atomic():
            expense.title = form_data["title"]
            expense.category = form_data["category"]
            expense.description = form_data["description"]
            expense.amount = form_data["amount"]
            expense.expense_date = form_data["expense_date"]
            expense.frequency = form_data["frequency"]
            expense.recurring_end_date = form_data["recurring_end_date"]

            expense.save()

            generate_recurring_expenses()

        messages.success(
            request,
            "Expense updated successfully.",
        )

        return redirect("expenses:expense_list")

    return render(
        request,
        "expenses/expense_form.html",
        expense_form_context(expense, {}, "Edit Expense"),
    )


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == "POST":
        with transaction.atomic():
            if expense.recurring_parent_id:
                # This is a generated occurrence: skip this period
                # and leave the original and other months untouched.
                parent = Expense.objects.select_for_update().get(
                    pk=expense.recurring_parent_id
                )

                period = expense.recurring_period
                skipped = list(parent.recurring_skipped_periods or [])

                if period and period not in skipped:
                    skipped.append(period)
                    parent.recurring_skipped_periods = skipped

                    parent.save(
                        update_fields=["recurring_skipped_periods"]
                    )

                expense.delete()

                success_message = (
                    "This recurring occurrence was deleted. "
                    "Other months remain unchanged."
                )

            elif expense.frequency in {"MONTHLY", "YEARLY"}:
                # Deleting the original removes its entire series.
                expense.delete()

                success_message = (
                    "The recurring expense and its generated entries "
                    "were deleted successfully."
                )

            else:
                expense.delete()

                success_message = "Expense deleted successfully."

        messages.success(request, success_message)
        return redirect("expenses:expense_list")

    return render(
        request,
        "expenses/expense_confirm_delete.html",
        {"expense": expense},
    )
