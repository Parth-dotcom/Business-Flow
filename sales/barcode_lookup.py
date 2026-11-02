import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from products.models import Product, ProductSize


logger = logging.getLogger(__name__)


@login_required
@require_GET
def barcode_lookup(request):
    """
    Look up a product or product-size barcode.

    Product barcode:
        Returns the product and its available sizes.

    Product-size barcode:
        Returns the product, exact size, and available stock.

    This endpoint only reads data. It does not change inventory.
    """

    barcode = request.GET.get("barcode", "").strip()

    if not barcode:
        return JsonResponse(
            {
                "success": False,
                "message": "Please scan or enter a barcode.",
            },
            status=400,
        )

    # First, check whether the barcode belongs to a specific size.
    size_row = (
        ProductSize.objects
        .select_related("product", "product__category")
        .filter(
            barcode=barcode,
            product__is_active=True,
        )
        .first()
    )

    if size_row:
        product = size_row.product

        if size_row.stock <= 0:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"{product.name}, size {size_row.size}, "
                        "is out of stock."
                    ),
                },
                status=409,
            )

        return JsonResponse(
            {
                "success": True,
                "barcode_type": "size",
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "barcode": product.barcode or "",
                    "price": str(product.price),
                    "stock": product.stock,
                },
                "size": {
                    "id": size_row.id,
                    "name": size_row.size,
                    "barcode": size_row.barcode or "",
                    "stock": size_row.stock,
                },
            }
        )

    # If no size barcode matched, check the product barcode.
    product = (
        Product.objects
        .select_related("category")
        .prefetch_related("sizes")
        .filter(
            barcode=barcode,
            is_active=True,
        )
        .first()
    )

    if product:
        sizes = [
            {
                "id": size.id,
                "name": size.size,
                "barcode": size.barcode or "",
                "stock": size.stock,
            }
            for size in product.sizes.all()
        ]

        available_sizes = [
            size for size in sizes
            if size["stock"] > 0
        ]

        if not available_sizes:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"{product.name} is currently out of stock."
                    ),
                },
                status=409,
            )

        return JsonResponse(
            {
                "success": True,
                "barcode_type": "product",
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "barcode": product.barcode or "",
                    "price": str(product.price),
                    "stock": product.stock,
                },
                "sizes": sizes,
            }
        )

    return JsonResponse(
        {
            "success": False,
            "message": f"No active product found for barcode: {barcode}",
        },
        status=404,
    )