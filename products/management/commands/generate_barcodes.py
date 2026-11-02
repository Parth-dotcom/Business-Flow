
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Product, ProductSize, generate_unique_barcode


class Command(BaseCommand):
    help = "Generate missing unique barcodes for products and product sizes."

    @transaction.atomic
    def handle(self, *args, **options):
        products_updated = 0
        sizes_updated = 0

        # Fill missing product barcodes without changing existing ones.
        for product in Product.objects.select_for_update().filter(
            barcode__isnull=True
        ).order_by("id"):
            product.barcode = self.generate_available_barcode()
            product.save(update_fields=["barcode"])
            products_updated += 1

        # Also handle empty strings left by earlier development attempts.
        for product in Product.objects.select_for_update().filter(
            barcode=""
        ).order_by("id"):
            product.barcode = self.generate_available_barcode()
            product.save(update_fields=["barcode"])
            products_updated += 1

        # Fill missing barcodes for each clothing size.
        for size in ProductSize.objects.select_for_update().filter(
            barcode__isnull=True
        ).order_by("id"):
            size.barcode = self.generate_available_barcode()
            size.save(update_fields=["barcode"])
            sizes_updated += 1

        for size in ProductSize.objects.select_for_update().filter(
            barcode=""
        ).order_by("id"):
            size.barcode = self.generate_available_barcode()
            size.save(update_fields=["barcode"])
            sizes_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. Product barcodes generated: {products_updated}; "
                f"size barcodes generated: {sizes_updated}."
            )
        )

    @staticmethod
    def generate_available_barcode():
        for _ in range(100):
            barcode = generate_unique_barcode()

            product_exists = Product.objects.filter(
                barcode=barcode
            ).exists()

            size_exists = ProductSize.objects.filter(
                barcode=barcode
            ).exists()

            if not product_exists and not size_exists:
                return barcode

        raise RuntimeError(
            "Unable to generate a unique barcode. Please try again."
        )
