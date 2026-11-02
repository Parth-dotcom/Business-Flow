from decimal import Decimal

from django.db import models
from django.utils.crypto import get_random_string


CLOTHING_SIZES = [
    ("XS", "XS"),
    ("S", "S"),
    ("M", "M"),
    ("L", "L"),
    ("XL", "XL"),
    ("2XL", "2XL"),
    ("3XL", "3XL"),
    ("4XL", "4XL"),
    ("5XL", "5XL"),
    ("6XL", "6XL"),
    ("7XL", "7XL"),
    ("8XL", "8XL"),
    ("FREE", "Free Size"),
]


def generate_unique_barcode():
    """Generate a barcode value for products and sizes."""
    return "AA" + get_random_string(
        12,
        allowed_chars="0123456789",
    )


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )

    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Barcode
    barcode = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        default=None,
        db_index=True,
    )

    # Selling price per unit
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    # Purchase cost per unit
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Additional expenses per unit
    transportation_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    packaging_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    other_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Total stock across all sizes.
    # Retained for compatibility with existing functionality.
    stock = models.PositiveIntegerField(default=0)

    low_stock_limit = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Generate a unique barcode if one has not been provided."""
        if not self.barcode:
            for _ in range(20):
                candidate = generate_unique_barcode()

                product_exists = Product.objects.filter(
                    barcode=candidate
                ).exists()

                size_exists = ProductSize.objects.filter(
                    barcode=candidate
                ).exists()

                if not product_exists and not size_exists:
                    self.barcode = candidate
                    break
            else:
                raise RuntimeError(
                    "Could not generate a unique product barcode."
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def true_cost_per_unit(self):
        """
        Calculate the total unit cost, including purchase cost
        and additional expenses.
        """
        return (
            self.cost_price
            + self.transportation_cost
            + self.packaging_cost
            + self.other_cost
        )

    @property
    def estimated_profit_per_unit(self):
        """Estimate profit per unit at the current selling price."""
        return self.price - self.true_cost_per_unit

    @property
    def estimated_profit_margin(self):
        """Calculate estimated profit margin as a percentage."""
        if self.price <= Decimal("0.00"):
            return Decimal("0.00")

        profit = self.estimated_profit_per_unit

        return (
            profit / self.price * Decimal("100")
        ).quantize(Decimal("0.01"))

    @property
    def profit_status(self):
        """Describe the estimated profit situation."""
        profit = self.estimated_profit_per_unit

        if profit < Decimal("0.00"):
            return "LOSS"

        if profit == Decimal("0.00"):
            return "BREAK_EVEN"

        return "PROFIT"

    @property
    def is_low_stock(self):
        return self.stock <= self.low_stock_limit


class ProductSize(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="sizes",
    )

    # Supports standard and custom clothing sizes.
    size = models.CharField(max_length=30)

    stock = models.PositiveIntegerField(default=0)

    barcode = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        default=None,
        db_index=True,
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size"],
                name="unique_size_per_product",
            )
        ]

    def save(self, *args, **kwargs):
        """Generate a unique barcode if one has not been provided."""
        if not self.barcode:
            for _ in range(20):
                candidate = generate_unique_barcode()

                product_exists = Product.objects.filter(
                    barcode=candidate
                ).exists()

                size_exists = ProductSize.objects.filter(
                    barcode=candidate
                ).exists()

                if not product_exists and not size_exists:
                    self.barcode = candidate
                    break
            else:
                raise RuntimeError(
                    "Could not generate a unique size barcode."
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.product.name} - {self.size} "
            f"(Stock: {self.stock})"
        )

    @property
    def true_cost_per_unit(self):
        """Return the parent product's total unit cost."""
        return self.product.true_cost_per_unit
