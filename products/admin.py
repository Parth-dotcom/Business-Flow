from django.contrib import admin
from .models import Category, Product, ProductSize


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
    )

    search_fields = (
        "name",
    )


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1
    fields = (
        "size",
        "stock",
        "barcode",
    )
    readonly_fields = (
        "barcode",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "price",
        "cost_price",
        "true_cost_per_unit",
        "estimated_profit_per_unit",
        "stock",
        "low_stock_limit",
        "is_active",
    )

    list_filter = (
        "category",
        "is_active",
    )

    search_fields = (
        "name",
        "sku",
        "barcode",
    )

    list_editable = (
        "price",
        "stock",
        "low_stock_limit",
        "is_active",
    )

    readonly_fields = (
        "barcode",
        "true_cost_per_unit",
        "estimated_profit_per_unit",
        "estimated_profit_margin",
        "profit_status",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Product Information",
            {
                "fields": (
                    "name",
                    "category",
                    "sku",
                    "description",
                    "barcode",
                    "is_active",
                )
            },
        ),
        (
            "Pricing and Expenses",
            {
                "fields": (
                    "price",
                    "cost_price",
                    "transportation_cost",
                    "packaging_cost",
                    "other_cost",
                    "true_cost_per_unit",
                    "estimated_profit_per_unit",
                    "estimated_profit_margin",
                    "profit_status",
                )
            },
        ),
        (
            "Inventory",
            {
                "fields": (
                    "stock",
                    "low_stock_limit",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [ProductSizeInline]

    @admin.display(description="True Unit Cost")
    def true_cost_per_unit(self, obj):
        if obj is None:
            return "-"
        return f"₹{obj.true_cost_per_unit:.2f}"

    @admin.display(description="Estimated Profit")
    def estimated_profit_per_unit(self, obj):
        if obj is None:
            return "-"
        return f"₹{obj.estimated_profit_per_unit:.2f}"

    @admin.display(description="Profit Margin")
    def estimated_profit_margin(self, obj):
        if obj is None:
            return "-"
        return f"{obj.estimated_profit_margin:.2f}%"

    @admin.display(description="Profit Status")
    def profit_status(self, obj):
        if obj is None:
            return "-"
        return obj.profit_status