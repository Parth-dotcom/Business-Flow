from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "amount",
        "expense_date",
        "created_by",
        "created_at",
    )

    list_filter = (
        "category",
        "expense_date",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
    )

    date_hierarchy = "expense_date"

    ordering = ("-expense_date",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Expense Details", {
            "fields": (
                "title",
                "category",
                "amount",
                "expense_date",
                "description",
            )
        }),
        ("Record Information", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )