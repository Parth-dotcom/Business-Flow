from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("MANAGER", "Manager"),
        ("SALES", "Sales"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="SALES",
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.username