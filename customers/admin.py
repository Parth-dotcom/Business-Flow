from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "city",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "city",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )

    list_editable = (
        "is_active",
    )

    ordering = (
        "-created_at",
    )