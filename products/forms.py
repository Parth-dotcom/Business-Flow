
from django import forms
from django.db import transaction
from .models import Category, Product, ProductSize, CLOTHING_SIZES


class ProductForm(forms.ModelForm):
    sizes = forms.MultipleChoiceField(
        choices=CLOTHING_SIZES,
        required=False,
        label="Available Sizes",
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "sku",
            "description",
            "price",
            "cost_price",
            "low_stock_limit",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
            "cost_price": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
            "low_stock_limit": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    @staticmethod
    def normalize_size(value):
        return " ".join(value.strip().upper().split())

    @staticmethod
    def stock_field_name(size):
        return "stock_" + size.replace(" ", "_").replace("-", "_")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.existing_sizes = {}
        self.size_stock_fields = {}
        self.size_rows = []

        if self.instance and self.instance.pk:
            self.existing_sizes = {
                item.size: item.stock
                for item in self.instance.sizes.all()
            }

        available_sizes = {
            size: label for size, label in CLOTHING_SIZES
        }

        for size in self.existing_sizes:
            available_sizes.setdefault(size, size)

        if self.is_bound:
            submitted_sizes = self.data.getlist("sizes")

            for raw_size in submitted_sizes:
                size = self.normalize_size(raw_size)
                if size and len(size) <= 30:
                    available_sizes.setdefault(size, size)

            self.fields["sizes"].initial = submitted_sizes
        else:
            self.fields["sizes"].initial = list(self.existing_sizes.keys())

        self.fields["sizes"].choices = list(available_sizes.items())

        for size, label in available_sizes.items():
            field_name = self.stock_field_name(size)

            self.fields[field_name] = forms.IntegerField(
                required=False,
                min_value=0,
                initial=self.existing_sizes.get(size, 0),
                label=f"{label} Stock",
                widget=forms.NumberInput(
                    attrs={
                        "class": "form-control size-stock-input",
                        "min": "0",
                        "step": "1",
                        "placeholder": "Enter quantity",
                    }
                ),
            )

            self.size_stock_fields[size] = field_name
            self.size_rows.append({
                "size": size,
                "label": label,
                "field": self[field_name],
                "key": field_name[6:],
            })

    def clean_sizes(self):
        result = []

        for raw_size in self.cleaned_data.get("sizes", []):
            size = self.normalize_size(raw_size)

            if not size:
                continue

            if len(size) > 30:
                raise forms.ValidationError(
                    f"Size '{size}' cannot exceed 30 characters."
                )

            if not all(c.isalnum() or c in " _-" for c in size):
                raise forms.ValidationError(
                    f"Size '{size}' contains invalid characters."
                )

            if size not in result:
                result.append(size)

        if len(result) > 50:
            raise forms.ValidationError(
                "You can select a maximum of 50 sizes per product."
            )

        return result

    def clean(self):
        cleaned_data = super().clean()
        selected_sizes = cleaned_data.get("sizes", [])

        # Check removed sizes before saving anything.
        removed_sizes = set(self.existing_sizes) - set(selected_sizes)

        for size in removed_sizes:
            size_record = ProductSize.objects.filter(
                product=self.instance,
                size=size,
            ).first()

            if not size_record:
                continue

            if size_record.stock > 0:
                self.add_error(
                    "sizes",
                    (
                        f"Cannot remove size {size}: "
                        f"{size_record.stock} pieces remain in stock. "
                        "Set its stock to zero first."
                    ),
                )
                continue

            # Check reverse relationships, including protected sale-item
            # relationships, without deleting the record.
            for relation in ProductSize._meta.related_objects:
                accessor = relation.get_accessor_name()

                if accessor == "+":
                    continue

                try:
                    related_manager = getattr(size_record, accessor)
                    if related_manager.exists():
                        self.add_error(
                            "sizes",
                            (
                                f"Cannot remove size {size}: it is referenced "
                                "by an existing record, such as a sale. "
                                "Keep it to preserve history."
                            ),
                        )
                        break
                except (AttributeError, TypeError):
                    continue

        total_stock = 0

        for size in selected_sizes:
            field_name = self.size_stock_fields.get(size)

            if not field_name:
                self.add_error("sizes", f"Missing stock field for size {size}.")
                continue

            quantity = cleaned_data.get(field_name)
            if quantity is None:
                quantity = 0
                cleaned_data[field_name] = 0

            total_stock += quantity

        if (
            self.instance
            and self.instance.pk
            and not self.existing_sizes
            and self.instance.stock > 0
            and selected_sizes
            and total_stock != self.instance.stock
        ):
            self.add_error(
                None,
                (
                    f"This product currently has {self.instance.stock} pieces "
                    "in stock. Allocate the existing stock across sizes so "
                    "the total remains unchanged."
                ),
            )

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        product = super().save(commit=False)
        selected_sizes = self.cleaned_data.get("sizes", [])

        is_legacy_product = (
            bool(product.pk)
            and not self.existing_sizes
            and product.stock > 0
            and not selected_sizes
        )

        if not is_legacy_product:
            product.stock = sum(
                self.cleaned_data.get(self.size_stock_fields[size]) or 0
                for size in selected_sizes
                if size in self.size_stock_fields
            )

        if not commit:
            return product

        product.save()
        self.save_m2m()

        existing_sizes = {
            item.size: item
            for item in ProductSize.objects.select_for_update().filter(
                product=product
            )
        }

        for size in selected_sizes:
            quantity = (
                self.cleaned_data.get(self.size_stock_fields[size]) or 0
            )

            if size in existing_sizes:
                item = existing_sizes[size]
                item.stock = quantity
                item.save(update_fields=["stock"])
            else:
                ProductSize.objects.create(
                    product=product,
                    size=size,
                    stock=quantity,
                )

        removed_sizes = set(existing_sizes) - set(selected_sizes)

        for size in removed_sizes:
            # Validation has already confirmed that removal is safe.
            existing_sizes[size].delete()

        if not is_legacy_product:
            product.stock = sum(
                item.stock for item in product.sizes.all()
            )
            product.save(update_fields=["stock", "updated_at"])

        return product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }
