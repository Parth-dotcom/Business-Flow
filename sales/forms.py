from django import forms

from .models import Sale, SaleItem


class SaleForm(forms.ModelForm):

    class Meta:
        model = Sale

        fields = [
            "customer",
            "discount",
            "tax",
            "payment_method",
        ]

        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "discount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter discount",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "tax": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter tax",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "payment_method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["customer"].required = False

        self.fields["customer"].queryset = (
            self.fields["customer"]
            .queryset
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["discount"].error_messages = {
            "required": "Discount is required.",
            "invalid": "Enter a valid discount.",
        }

        self.fields["tax"].error_messages = {
            "required": "Tax is required.",
            "invalid": "Enter a valid tax amount.",
        }

    def clean_discount(self):
        discount = self.cleaned_data["discount"]

        if discount < 0:
            raise forms.ValidationError(
                "Discount cannot be negative."
            )

        return discount

    def clean_tax(self):
        tax = self.cleaned_data["tax"]

        if tax < 0:
            raise forms.ValidationError(
                "Tax cannot be negative."
            )

        return tax


class SaleItemForm(forms.ModelForm):

    class Meta:
        model = SaleItem

        fields = [
            "product",
            "quantity",
        ]

        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter quantity",
                    "min": "1",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["product"].queryset = (
            self.fields["product"]
            .queryset
            .filter(is_active=True)
            .order_by("name")
        )

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least 1."
            )

        return quantity