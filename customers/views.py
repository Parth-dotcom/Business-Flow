from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from sales.models import Sale

from .forms import CustomerForm
from .models import Customer


# =========================================================
# CUSTOMER LIST
# =========================================================

@login_required
def customer_list(request):

    search = request.GET.get(
        "search",
        ""
    ).strip()

    customers = Customer.objects.all()

    if search:

        customers = (
            customers.filter(
                name__icontains=search
            )
            | customers.filter(
                phone__icontains=search
            )
            | customers.filter(
                email__icontains=search
            )
            | customers.filter(
                city__icontains=search
            )
        )

    customers = customers.order_by(
        "-created_at"
    )

    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": customers,
            "search": search,
        }
    )


# =========================================================
# CUSTOMER CREATE
# =========================================================

@login_required
def customer_create(request):

    if request.method == "POST":

        form = CustomerForm(
            request.POST
        )

        if form.is_valid():

            customer = form.save()

            messages.success(
                request,
                f"Customer {customer.name} "
                f"created successfully."
            )

            return redirect(
                "customer_list"
            )

    else:

        form = CustomerForm()

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "title": "Add Customer",
            "button_text": "Save Customer",
        }
    )


# =========================================================
# CUSTOMER EDIT
# =========================================================

@login_required
def customer_edit(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk
    )

    if request.method == "POST":

        form = CustomerForm(
            request.POST,
            instance=customer
        )

        if form.is_valid():

            customer = form.save()

            messages.success(
                request,
                f"Customer {customer.name} "
                f"updated successfully."
            )

            return redirect(
                "customer_detail",
                pk=customer.pk
            )

    else:

        form = CustomerForm(
            instance=customer
        )

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "customer": customer,
            "title": "Edit Customer",
            "button_text": "Update Customer",
        }
    )


# =========================================================
# CUSTOMER DETAIL
# =========================================================

@login_required
def customer_detail(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk
    )

    # All invoices belonging to this customer
    sales = (
        Sale.objects
        .filter(
            customer=customer
        )
        .select_related(
            "created_by"
        )
        .prefetch_related(
            "items__product"
        )
        .order_by(
            "-created_at"
        )
    )

    # Total amount purchased
    purchase_summary = sales.aggregate(
        total_purchases=Sum(
            "total_amount"
        )
    )

    total_purchases = (
        purchase_summary["total_purchases"]
        if purchase_summary["total_purchases"] is not None
        else 0
    )

    # Total number of invoices
    total_invoices = sales.count()

    context = {
        "customer": customer,
        "sales": sales,
        "total_purchases": total_purchases,
        "total_invoices": total_invoices,
    }

    return render(
        request,
        "customers/customer_detail.html",
        context
    )


# =========================================================
# CUSTOMER DELETE
# =========================================================

@login_required
def customer_delete(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk
    )

    # Do not allow deletion if invoices
    # are linked to this customer.
    if Sale.objects.filter(
        customer=customer
    ).exists():

        messages.error(
            request,
            "This customer cannot be deleted "
            "because sales invoices are linked "
            "to this customer."
        )

        return redirect(
            "customer_detail",
            pk=customer.pk
        )

    if request.method == "POST":

        customer_name = customer.name

        customer.delete()

        messages.success(
            request,
            f"Customer {customer_name} "
            f"deleted successfully."
        )

        return redirect(
            "customer_list"
        )

    return render(
        request,
        "customers/customer_confirm_delete.html",
        {
            "customer": customer,
        }
    )