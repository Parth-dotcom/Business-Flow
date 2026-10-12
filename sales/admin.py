from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer",
        "created_by",
        "subtotal",
        "discount",
        "tax",
        "total_amount",
        "payment_method",
        "created_at",
    )

    list_filter = (
        "payment_method",
        "created_at",
    )

    search_fields = (
        "invoice_number",
        "customer__name",
        "customer__phone",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = [
        SaleItemInline,
    ]


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = (
        "sale",
        "product",
        "quantity",
        "unit_price",
        "total_price",
    )

    search_fields = (
        "sale__invoice_number",
        "product__name",
    )