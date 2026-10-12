from django import forms

from .models import Category, Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "name",
            "category",
            "sku",
            "description",
            "price",
            "cost_price",
            "stock",
            "low_stock_limit",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter product name",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: WM-001",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter product description",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter selling price",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "cost_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter purchase cost",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter stock quantity",
                    "min": "0",
                }
            ),
            "low_stock_limit": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 5",
                    "min": "0",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["stock"].error_messages = {
            "min_value": "Stock cannot be negative.",
            "required": "Stock quantity is required.",
            "invalid": "Enter a valid stock quantity.",
        }

        self.fields["price"].error_messages = {
            "required": "Selling price is required.",
            "invalid": "Enter a valid price.",
        }

        self.fields["cost_price"].error_messages = {
            "required": "Purchase cost is required.",
            "invalid": "Enter a valid purchase cost.",
        }

        self.fields["low_stock_limit"].error_messages = {
            "min_value": "Low stock limit cannot be negative.",
            "required": "Low stock limit is required.",
            "invalid": "Enter a valid low stock limit.",
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 2:
            raise forms.ValidationError(
                "Product name must contain at least 2 characters."
            )

        return name

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip().upper()

        if len(sku) < 2:
            raise forms.ValidationError(
                "SKU must contain at least 2 characters."
            )

        return sku

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price < 0:
            raise forms.ValidationError(
                "Selling price cannot be negative."
            )

        return price

    def clean_cost_price(self):
        cost_price = self.cleaned_data["cost_price"]

        if cost_price < 0:
            raise forms.ValidationError(
                "Purchase cost cannot be negative."
            )

        return cost_price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]

        if stock < 0:
            raise forms.ValidationError(
                "Stock cannot be negative."
            )

        return stock

    def clean_low_stock_limit(self):
        low_stock_limit = self.cleaned_data["low_stock_limit"]

        if low_stock_limit < 0:
            raise forms.ValidationError(
                "Low stock limit cannot be negative."
            )

        return low_stock_limit


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category

        fields = [
            "name",
            "description",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Electronics",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter category description",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 2:
            raise forms.ValidationError(
                "Category name must contain at least 2 characters."
            )

        existing_category = Category.objects.filter(
            name__iexact=name
        ).exclude(
            pk=self.instance.pk
        )

        if existing_category.exists():
            raise forms.ValidationError(
                "A category with this name already exists."
            )

        return name
