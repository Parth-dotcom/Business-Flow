
from django.db.models import F

from products.models import Product


def inventory_notifications(request):
    """
    Supply real inventory alerts to the templates.
    Only active products at or below their stock limit are included.
    """

    empty_result = {
        "low_stock_products": [],
        "low_stock_count": 0,
        "out_of_stock_count": 0,
        "low_stock_only_count": 0,
    }

    if not request.user.is_authenticated:
        return empty_result

    low_stock_products = list(
        Product.objects.filter(
            is_active=True,
            stock__lte=F("low_stock_limit"),
        ).order_by("stock", "name")
    )

    out_of_stock_count = sum(
        1 for product in low_stock_products
        if product.stock == 0
    )

    low_stock_count = len(low_stock_products)

    return {
        "low_stock_products": low_stock_products,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_only_count": (
            low_stock_count - out_of_stock_count
        ),
    }
