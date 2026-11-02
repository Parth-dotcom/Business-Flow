import base64
from decimal import Decimal, InvalidOperation
from io import BytesIO

import barcode
from barcode.writer import SVGWriter

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.shortcuts import redirect, render, get_object_or_404

from .forms import CategoryForm, ProductForm
from .models import Category, Product, ProductSize


def make_barcode_svg(value):
    """Return a base64-encoded Code 128 barcode SVG."""
    if not value:
        return ""

    output = BytesIO()
    code = barcode.get("code128", str(value), writer=SVGWriter())
    code.write(
        output,
        options={
            "module_width": 0.30,
            "module_height": 12,
            "quiet_zone": 2,
            "write_text": False,
        },
    )
    return base64.b64encode(output.getvalue()).decode("ascii")


@login_required
def barcode_labels(request):
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    label_type = request.GET.get("type", "all")

    products = (
        Product.objects.select_related("category")
        .prefetch_related("sizes")
        .filter(is_active=True)
    )

    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(barcode__icontains=search)
            | Q(sizes__barcode__icontains=search)
        ).distinct()

    if category:
        products = products.filter(category_id=category)

    products = products.order_by("name")
    labels = []

    for product in products:
        if label_type in ("all", "product") and product.barcode:
            labels.append({
                "product": product,
                "name": product.name,
                "sku": product.sku,
                "size": "",
                "price": product.price,
                "barcode": product.barcode,
                "barcode_image": make_barcode_svg(product.barcode),
                "kind": "Product",
            })

        if label_type in ("all", "size"):
            for size in product.sizes.all():
                if not size.barcode:
                    continue
                labels.append({
                    "product": product,
                    "name": product.name,
                    "sku": product.sku,
                    "size": size.size,
                    "price": product.price,
                    "barcode": size.barcode,
                    "barcode_image": make_barcode_svg(size.barcode),
                    "kind": "Size",
                })

    categories = Category.objects.all().order_by("name")
    return render(
        request,
        "products/barcode_labels.html",
        {
            "labels": labels,
            "categories": categories,
            "search": search,
            "selected_category": category,
            "label_type": label_type,
        },
    )


@login_required
def product_list(request):
    search = request.GET.get("search", "")
    low_stock = request.GET.get("low_stock", "")
    category = request.GET.get("category", "")
    per_page = request.GET.get("per_page", "10")

    try:
        per_page = int(per_page)
    except (TypeError, ValueError):
        per_page = 10

    if per_page not in [10, 25, 50, 100]:
        per_page = 10

    products = Product.objects.select_related("category").all()

    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(category__name__icontains=search)
        )

    if low_stock == "1":
        products = products.filter(stock__lte=F("low_stock_limit"))

    if category:
        products = products.filter(category_id=category)

    products = products.order_by("-created_at")
    paginator = Paginator(products, per_page)
    products_page = paginator.get_page(request.GET.get("page"))
    categories = Category.objects.all().order_by("name")

    return render(
        request,
        "products/product_list.html",
        {
            "products": products_page,
            "categories": categories,
            "per_page": per_page,
        },
    )


@login_required
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("sizes"),
        pk=pk,
    )
    return render(
        request,
        "products/product_detail.html",
        {"product": product},
    )


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm()

    return render(request, "products/product_form.html", {"form": form})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "products/product_form.html",
        {"form": form, "product": product},
    )


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.delete()
        return redirect("product_list")

    return render(
        request,
        "products/product_confirm_delete.html",
        {"product": product},
    )


@login_required
def category_list(request):
    search = request.GET.get("search", "").strip()
    categories = Category.objects.all()

    if search:
        categories = categories.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    categories = categories.order_by("name")
    return render(
        request,
        "products/category_list.html",
        {"categories": categories},
    )


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("category_list")
    else:
        form = CategoryForm()

    return render(
        request,
        "products/category_form.html",
        {"form": form},
    )


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "products/category_form.html",
        {"form": form, "category": category},
    )


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    product_count = category.products.count()

    if request.method == "POST":
        if product_count > 0:
            return redirect("category_list")
        category.delete()
        return redirect("category_list")

    return render(
        request,
        "products/category_confirm_delete.html",
        {"category": category, "product_count": product_count},
    )


def _as_decimal(value, default=Decimal("0.00")):
    """Safely parse a user-supplied decimal value."""
    try:
        parsed = Decimal(str(value).strip())
        if not parsed.is_finite():
            return default
        return parsed
    except (InvalidOperation, TypeError, ValueError):
        return default


@login_required
def smart_profit_advisor(request):
    """Calculate unit costs, target-margin prices, and discount profitability."""
    active_products = Product.objects.filter(is_active=True).select_related(
        "category"
    ).order_by("name")

    selected_product_id = request.GET.get("product", "").strip()
    selected_product = None

    if selected_product_id:
        try:
            selected_product = active_products.filter(
                pk=int(selected_product_id)
            ).first()
        except (TypeError, ValueError):
            selected_product = None

    if selected_product is None:
        selected_product = active_products.first()

    purchase_cost = (
        _as_decimal(selected_product.cost_price)
        if selected_product else Decimal("0.00")
    )
    transportation_cost = (
        _as_decimal(selected_product.transportation_cost)
        if selected_product else Decimal("0.00")
    )
    packaging_cost = (
        _as_decimal(selected_product.packaging_cost)
        if selected_product else Decimal("0.00")
    )
    other_cost = (
        _as_decimal(selected_product.other_cost)
        if selected_product else Decimal("0.00")
    )
    current_price = (
        _as_decimal(selected_product.price)
        if selected_product else Decimal("0.00")
    )

    true_unit_cost = (
        purchase_cost + transportation_cost + packaging_cost + other_cost
    )

    margin_input = request.GET.get("margin", "30")
    margin_percent = _as_decimal(margin_input, Decimal("30"))
    margin_error = ""

    if margin_percent < 0 or margin_percent >= 100:
        margin_error = "Enter a target margin of at least 0% and less than 100%."
        margin_percent = Decimal("30")

    if true_unit_cost > 0:
        suggested_price = (
            true_unit_cost / (Decimal("1") - margin_percent / Decimal("100"))
        ).quantize(Decimal("0.01"))
    else:
        suggested_price = Decimal("0.00")

    discount_type = request.GET.get("discount_type", "percentage")
    if discount_type not in ("percentage", "fixed"):
        discount_type = "percentage"

    discount_input = request.GET.get("discount", "0")
    discount_amount_input = _as_decimal(discount_input)
    discount_error = ""

    if discount_amount_input < 0:
        discount_error = "Discount cannot be negative."
        discount_amount_input = Decimal("0.00")

    if discount_type == "percentage":
        if discount_amount_input > 100:
            discount_error = "Percentage discount cannot exceed 100%."
            discount_amount_input = Decimal("100")
        discount_value = (
            current_price * discount_amount_input / Decimal("100")
        )
    else:
        if current_price > 0 and discount_amount_input > current_price:
            discount_error = "Fixed discount cannot exceed the selling price."
            discount_amount_input = current_price
        discount_value = discount_amount_input

    discounted_price = max(
        Decimal("0.00"), current_price - discount_value
    ).quantize(Decimal("0.01"))
    estimated_profit = (discounted_price - true_unit_cost).quantize(
        Decimal("0.01")
    )
    if estimated_profit < 0:
        profit_status = "loss"
        profit_message = "Warning: the discounted price is below the true unit cost."
    elif estimated_profit == 0:
        profit_status = "break_even"
        profit_message = "Break-even: there is no estimated profit after the discount."
    else:
        profit_status = "profit"
        profit_message = "This discounted price remains above the true unit cost."

    if discounted_price > 0:
        discounted_margin = (
            estimated_profit / discounted_price * Decimal("100")
        ).quantize(Decimal("0.01"))
    else:
        discounted_margin = Decimal("0.00")

    context = {
        "products": active_products,
        "selected_product": selected_product,
        "selected_product_id": str(selected_product.pk) if selected_product else "",
        "purchase_cost": purchase_cost,
        "transportation_cost": transportation_cost,
        "packaging_cost": packaging_cost,
        "other_cost": other_cost,
        "true_unit_cost": true_unit_cost.quantize(Decimal("0.01")),
        "current_price": current_price,
        "margin_input": margin_input,
        "margin_percent": margin_percent,
        "margin_error": margin_error,
        "suggested_price": suggested_price,
        "discount_type": discount_type,
        "discount_input": discount_input,
        "discount_value": discount_value.quantize(Decimal("0.01")),
        "discounted_price": discounted_price,
        "estimated_profit": estimated_profit,
        "discounted_margin": discounted_margin,
        "profit_status": profit_status,
        "profit_message": profit_message,
        "discount_error": discount_error,
    }
    return render(request, "products/smart_profit_advisor.html", context)
