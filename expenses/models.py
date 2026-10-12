
from django.conf import settings
from django.db import models


class Expense(models.Model):

    CATEGORY_CHOICES = [
        ("Rent", "Rent"),
        ("Electricity", "Electricity"),
        ("Salary", "Salary"),
        ("Transport", "Transport"),
        ("Packaging", "Packaging"),
        ("Marketing", "Marketing"),
        ("Maintenance", "Maintenance"),
        ("Internet", "Internet"),
        ("Travel", "Travel"),
        ("Other", "Other"),
    ]

    FREQUENCY_CHOICES = [
        ("ONCE", "One-time"),
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
    ]

    title = models.CharField(max_length=200)

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="Other",
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    expense_date = models.DateField()

    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default="ONCE",
    )

    recurring_end_date = models.DateField(
        blank=True,
        null=True,
    )

    recurring_parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="generated_entries",
    )

    recurring_period = models.CharField(
        max_length=7,
        blank=True,
        default="",
    )

    recurring_skipped_periods = models.JSONField(
        default=list,
        blank=True,
        help_text="Periods intentionally skipped for this recurring expense.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_expenses",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"
