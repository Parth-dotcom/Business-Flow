
from django.db import models


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

    price = models.DecimalField(max_digits=10, decimal_places=2)

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )

    # Total stock across all sizes.
    # Retained for compatibility with the existing system.
    stock = models.PositiveIntegerField(default=0)

    low_stock_limit = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return self.stock <= self.low_stock_limit


class ProductSize(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="sizes",
    )

    # Custom sizes are supported.
    # The size field is no longer restricted to predefined choices.
    size = models.CharField(max_length=30)

    stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size"],
                name="unique_size_per_product",
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size} (Stock: {self.stock})"
