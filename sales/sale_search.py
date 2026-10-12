from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone

from .models import Sale


@login_required
def sale_search(request):

    search = request.GET.get(
        "search",
        ""
    ).strip()

    payment_method = request.GET.get(
        "payment_method",
        "ALL"
    ).strip().upper()

    start_date = request.GET.get(
        "start_date",
        ""
    ).strip()

    end_date = request.GET.get(
        "end_date",
        ""
    ).strip()

    valid_payment_methods = {
        "ALL",
        "CASH",
        "CARD",
        "UPI",
        "OTHER",
    }

    if payment_method not in valid_payment_methods:
        payment_method = "ALL"

    sales = (
        Sale.objects
        .select_related(
            "customer",
            "created_by",
        )
        .prefetch_related(
            "items__product",
        )
        .order_by("-created_at")
    )

    # =========================================
    # SEARCH FILTER
    # =========================================

    if search:

        sales = sales.filter(
            Q(invoice_number__icontains=search)
            | Q(customer__name__icontains=search)
            | Q(customer__phone__icontains=search)
        )

    # =========================================
    # PAYMENT FILTER
    # =========================================

    if payment_method != "ALL":

        sales = sales.filter(
            payment_method=payment_method
        )

    # =========================================
    # START DATE FILTER
    # =========================================

    if start_date:

        try:

            start_date_obj = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

            start_datetime = timezone.make_aware(
                datetime.combine(
                    start_date_obj,
                    datetime.min.time()
                )
            )

            sales = sales.filter(
                created_at__gte=start_datetime
            )

        except ValueError:

            start_date = ""

    # =========================================
    # END DATE FILTER
    # =========================================

    if end_date:

        try:

            end_date_obj = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date()

            end_datetime = timezone.make_aware(
                datetime.combine(
                    end_date_obj + timedelta(days=1),
                    datetime.min.time()
                )
            )

            sales = sales.filter(
                created_at__lt=end_datetime
            )

        except ValueError:

            end_date = ""

    # =========================================
    # SALES SUMMARY
    # =========================================

    total_invoices = sales.count()

    total_sales = sales.aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0.00")

    cash_sales = sales.filter(
        payment_method="CASH"
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0.00")

    card_sales = sales.filter(
        payment_method="CARD"
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0.00")

    upi_sales = sales.filter(
        payment_method="UPI"
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0.00")

    return render(
        request,
        "sales/sale_search.html",
        {
            "sales": sales,
            "search": search,
            "payment_method": payment_method,
            "start_date": start_date,
            "end_date": end_date,

            "total_invoices": total_invoices,
            "total_sales": total_sales,
            "cash_sales": cash_sales,
            "card_sales": card_sales,
            "upi_sales": upi_sales,
        },
    )