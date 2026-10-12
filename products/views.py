from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.shortcuts import redirect, render, get_object_or_404

from .forms import CategoryForm, ProductForm
from .models import Category, Product


@login_required
def product_list(request):
    search = request.GET.get("search", "")
    low_stock = request.GET.get("low_stock", "")
    category = request.GET.get("category", "")

    per_page = request.GET.get("per_page", "10")

    try:
        per_page = int(per_page)
    except ValueError:
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
        products = products.filter(
            stock__lte=F("low_stock_limit")
        )

    if category:
        products = products.filter(
            category_id=category
        )

    products = products.order_by("-created_at")

    paginator = Paginator(products, per_page)

    page_number = request.GET.get("page")
    products_page = paginator.get_page(page_number)

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
        Product.objects.select_related("category"),
        pk=pk
    )

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
        },
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

    return render(
        request,
        "products/product_form.html",
        {
            "form": form,
        },
    )


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(
            request.POST,
            instance=product
        )

        if form.is_valid():
            form.save()
            return redirect("product_list")

    else:
        form = ProductForm(
            instance=product
        )

    return render(
        request,
        "products/product_form.html",
        {
            "form": form,
            "product": product,
        },
    )


@login_required
def product_delete(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk
    )

    if request.method == "POST":
        product.delete()
        return redirect("product_list")

    return render(
        request,
        "products/product_confirm_delete.html",
        {
            "product": product,
        },
    )


@login_required
def category_list(request):
    search = request.GET.get("search", "")

    categories = Category.objects.all()

    if search:
        categories = categories.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
        )

    categories = categories.order_by("name")

    return render(
        request,
        "products/category_list.html",
        {
            "categories": categories,
        },
    )


@login_required
def category_create(request):
    if request.method == "POST":

        form = CategoryForm(
            request.POST
        )

        if form.is_valid():
            form.save()
            return redirect("category_list")

    else:
        form = CategoryForm()

    return render(
        request,
        "products/category_form.html",
        {
            "form": form,
        },
    )


@login_required
def category_edit(request, pk):
    category = get_object_or_404(
        Category,
        pk=pk
    )

    if request.method == "POST":

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():
            form.save()
            return redirect("category_list")

    else:

        form = CategoryForm(
            instance=category
        )

    return render(
        request,
        "products/category_form.html",
        {
            "form": form,
            "category": category,
        },
    )


@login_required
def category_delete(request, pk):
    category = get_object_or_404(
        Category,
        pk=pk
    )

    product_count = category.products.count()

    if request.method == "POST":

        if product_count > 0:
            return redirect("category_list")

        category.delete()

        return redirect("category_list")

    return render(
        request,
        "products/category_confirm_delete.html",
        {
            "category": category,
            "product_count": product_count,
        },
    )